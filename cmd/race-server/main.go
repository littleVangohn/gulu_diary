package main

import (
	"bufio"
	"context"
	"crypto/hmac"
	"crypto/md5"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/valyala/fasthttp"
	"github.com/valyala/fastjson"
)

type Config struct {
	Host              string
	Port              int
	Secret            string
	DeviceCSVPath     string
	TicketTTL         time.Duration
	TokenTTL          time.Duration
	StrictSignature   bool
	StrictToken       bool
	RedisAddr         string
	RedisPassword     string
	RedisDB           int
	RedisPoolSize     int
	RedisMinIdleConns int
	RedisWriteMode    string
	TicketPrefix      string
	DataPrefix        string
}

type Server struct {
	cfg           Config
	redis         *redis.Client
	deviceSecrets map[string]string
}

type responseEnvelope struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

type tokenPayload struct {
	Kind       string
	DeviceID   string
	ExpiredSec int64
	Signature  string
}

func main() {
	cfg := loadConfig()
	rdb := redis.NewClient(&redis.Options{
		Addr:         cfg.RedisAddr,
		Password:     cfg.RedisPassword,
		DB:           cfg.RedisDB,
		PoolSize:     cfg.RedisPoolSize,
		MinIdleConns: cfg.RedisMinIdleConns,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Fatalf("redis ping failed: %v", err)
	}

	deviceSecrets, err := loadDeviceSecrets(cfg.DeviceCSVPath)
	if err != nil {
		log.Fatalf("load device secrets failed: %v", err)
	}

	s := &Server{
		cfg:           cfg,
		redis:         rdb,
		deviceSecrets: deviceSecrets,
	}

	server := &fasthttp.Server{
		Name:                          "competition-race",
		Handler:                       s.handle,
		ReadTimeout:                   3 * time.Second,
		WriteTimeout:                  3 * time.Second,
		MaxRequestBodySize:            1 << 20,
		NoDefaultServerHeader:         true,
		DisableHeaderNamesNormalizing: true,
	}

	addr := fmt.Sprintf("%s:%d", cfg.Host, cfg.Port)
	log.Printf("race server listening on %s", addr)
	log.Fatal(server.ListenAndServe(addr))
}

func loadConfig() Config {
	return Config{
		Host:              getEnv("HOST", "0.0.0.0"),
		Port:              getEnvInt("PORT", 5000),
		Secret:            getEnv("SECRET", "comp2026"),
		DeviceCSVPath:     getEnv("DEVICE_CSV_PATH", "data/devices.csv"),
		TicketTTL:         time.Duration(getEnvInt("TICKET_TTL_SECONDS", 300)) * time.Second,
		TokenTTL:          time.Duration(getEnvInt("TOKEN_TTL_SECONDS", 7200)) * time.Second,
		StrictSignature:   getEnvBool("STRICT_SIGNATURE", true),
		StrictToken:       getEnvBool("STRICT_TOKEN", true),
		RedisAddr:         getEnv("REDIS_ADDR", "127.0.0.1:6379"),
		RedisPassword:     os.Getenv("REDIS_PASSWORD"),
		RedisDB:           getEnvInt("REDIS_DB", 0),
		RedisPoolSize:     getEnvInt("REDIS_POOL_SIZE", 256),
		RedisMinIdleConns: getEnvInt("REDIS_MIN_IDLE_CONNS", 32),
		RedisWriteMode:    strings.ToLower(getEnv("REDIS_WRITE_MODE", "list")),
		TicketPrefix:      getEnv("TICKET_PREFIX", "ct:"),
		DataPrefix:        getEnv("DATA_PREFIX", "competition:bp:"),
	}
}

func (s *Server) handle(ctx *fasthttp.RequestCtx) {
	switch string(ctx.Path()) {
	case "/healthz":
		s.handleHealth(ctx)
	case "/getTicket":
		if !ctx.IsGet() {
			s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
			return
		}
		s.handleGetTicket(ctx)
	case "/getToken":
		if !ctx.IsPost() {
			s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
			return
		}
		s.handleGetToken(ctx)
	case "/uploadData":
		if !ctx.IsPost() {
			s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
			return
		}
		s.handleUploadData(ctx)
	case "/refreshToken":
		if !ctx.IsPost() {
			s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
			return
		}
		s.handleRefreshToken(ctx)
	default:
		ctx.SetStatusCode(fasthttp.StatusNotFound)
	}
}

func (s *Server) handleHealth(ctx *fasthttp.RequestCtx) {
	s.writeJSON(ctx, fasthttp.StatusOK, 200, "成功", map[string]string{"status": "ok"})
}

func (s *Server) handleGetTicket(ctx *fasthttp.RequestCtx) {
	deviceID := strings.TrimSpace(string(ctx.QueryArgs().Peek("deviceId")))
	if deviceID == "" {
		s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
		return
	}
	if _, ok := s.deviceSecrets[deviceID]; !ok {
		s.writeJSON(ctx, fasthttp.StatusOK, 202, "未知设备Id", nil)
		return
	}

	ticket, err := randomToken(24)
	if err != nil {
		s.writeJSON(ctx, fasthttp.StatusInternalServerError, 500, "服务端异常", nil)
		return
	}

	redisKey := s.cfg.TicketPrefix + ticket
	if err := s.redis.Set(context.Background(), redisKey, deviceID, s.cfg.TicketTTL).Err(); err != nil {
		s.writeJSON(ctx, fasthttp.StatusInternalServerError, 500, "服务端异常", nil)
		return
	}

	s.writeJSON(ctx, fasthttp.StatusOK, 200, "成功", map[string]string{"ticket": ticket})
}

func (s *Server) handleGetToken(ctx *fasthttp.RequestCtx) {
	v, ok := s.parseJSONBody(ctx)
	if !ok {
		s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
		return
	}

	deviceID := strings.TrimSpace(string(v.GetStringBytes("deviceId")))
	signature := strings.TrimSpace(string(v.GetStringBytes("signature")))
	ticket := strings.TrimSpace(string(v.GetStringBytes("ticket")))

	if deviceID == "" || signature == "" || ticket == "" {
		s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
		return
	}
	deviceSecret, ok := s.deviceSecrets[deviceID]
	if !ok {
		s.writeJSON(ctx, fasthttp.StatusOK, 202, "未知设备Id", nil)
		return
	}

	if s.cfg.StrictSignature {
		expected := md5HexParts(ticket, deviceID, deviceSecret)
		if !strings.EqualFold(signature, expected) {
			s.writeJSON(ctx, fasthttp.StatusOK, 203, "签名解析失败", nil)
			return
		}
	}

	redisKey := s.cfg.TicketPrefix + ticket
	storedDeviceID, err := s.redis.GetDel(context.Background(), redisKey).Result()
	if err == redis.Nil {
		s.writeJSON(ctx, fasthttp.StatusOK, 202, "未知设备Id", nil)
		return
	}
	if err != nil {
		s.writeJSON(ctx, fasthttp.StatusInternalServerError, 500, "服务端异常", nil)
		return
	}
	if storedDeviceID != deviceID {
		s.writeJSON(ctx, fasthttp.StatusOK, 202, "未知设备Id", nil)
		return
	}

	expiredSec := time.Now().Add(s.cfg.TokenTTL).Unix()
	token := s.makeToken("0", deviceID, deviceSecret, expiredSec)
	s.writeJSON(ctx, fasthttp.StatusOK, 200, "成功", map[string]interface{}{
		"token":       token,
		"expiredTime": expiredSec,
	})
}

func (s *Server) handleUploadData(ctx *fasthttp.RequestCtx) {
	v, ok := s.parseJSONBody(ctx)
	if !ok {
		s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
		return
	}

	deviceID := strings.TrimSpace(string(v.GetStringBytes("deviceId")))
	token := strings.TrimSpace(string(v.GetStringBytes("token")))
	timeValue := v.GetInt64("data", "time")
	high := v.GetInt("data", "high")
	low := v.GetInt("data", "low")

	if deviceID == "" || token == "" || timeValue == 0 || high == 0 || low == 0 {
		s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
		return
	}
	deviceSecret, ok := s.deviceSecrets[deviceID]
	if !ok {
		s.writeJSON(ctx, fasthttp.StatusOK, 202, "未知设备Id", nil)
		return
	}

	if high < low || high <= 0 || low <= 0 {
		s.writeJSON(ctx, fasthttp.StatusOK, 205, "血压值不正确", nil)
		return
	}

	if s.cfg.StrictToken {
		payload, valid, expired := s.parseAndValidateToken(token, deviceSecret)
		if !valid {
			s.writeJSON(ctx, fasthttp.StatusOK, 204, "会话token无效", nil)
			return
		}
		if expired {
			s.writeJSON(ctx, fasthttp.StatusOK, 206, "token超期", nil)
			return
		}
		if payload.DeviceID != deviceID {
			s.writeJSON(ctx, fasthttp.StatusOK, 204, "会话token无效", nil)
			return
		}
	}

	receivedTime := time.Now().UnixMilli()
	key := s.cfg.DataPrefix + deviceID
	if s.cfg.RedisWriteMode == "stream" {
		args := &redis.XAddArgs{
			Stream: key,
			Values: map[string]interface{}{
				"deviceId":     deviceID,
				"time":         timeValue,
				"high":         high,
				"low":          low,
				"receivedTime": receivedTime,
			},
		}
		if err := s.redis.XAdd(context.Background(), args).Err(); err != nil {
			s.writeJSON(ctx, fasthttp.StatusInternalServerError, 500, "服务端异常", nil)
			return
		}
	} else {
		record := encodeCompactRecord(timeValue, high, low, receivedTime)
		if err := s.redis.RPush(context.Background(), key, record).Err(); err != nil {
			s.writeJSON(ctx, fasthttp.StatusInternalServerError, 500, "服务端异常", nil)
			return
		}
	}

	s.writeJSON(ctx, fasthttp.StatusOK, 200, "成功", map[string]int64{"receivedTime": receivedTime})
}

func (s *Server) handleRefreshToken(ctx *fasthttp.RequestCtx) {
	v, ok := s.parseJSONBody(ctx)
	if !ok {
		s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
		return
	}

	deviceID := strings.TrimSpace(string(v.GetStringBytes("deviceId")))
	signature := strings.TrimSpace(string(v.GetStringBytes("signature")))
	token := strings.TrimSpace(string(v.GetStringBytes("token")))

	if deviceID == "" || signature == "" || token == "" {
		s.writeJSON(ctx, fasthttp.StatusOK, 201, "缺少参数", nil)
		return
	}
	deviceSecret, ok := s.deviceSecrets[deviceID]
	if !ok {
		s.writeJSON(ctx, fasthttp.StatusOK, 202, "未知设备Id", nil)
		return
	}

	if s.cfg.StrictSignature {
		expected := md5HexParts(token, deviceID, deviceSecret)
		if !strings.EqualFold(signature, expected) {
			s.writeJSON(ctx, fasthttp.StatusOK, 203, "签名解析失败", nil)
			return
		}
	}

	payload, valid, expired := s.parseAndValidateToken(token, deviceSecret)
	if !valid || payload.DeviceID != deviceID {
		s.writeJSON(ctx, fasthttp.StatusOK, 202, "未知设备Id", nil)
		return
	}
	if expired {
		s.writeJSON(ctx, fasthttp.StatusOK, 206, "token超期", nil)
		return
	}
	if payload.Kind != "0" {
		s.writeJSON(ctx, fasthttp.StatusOK, 207, "不能用此token再次请求token，请重新取票获取", nil)
		return
	}

	expiredSec := time.Now().Add(s.cfg.TokenTTL).Unix()
	newToken := s.makeToken("1", deviceID, deviceSecret, expiredSec)
	s.writeJSON(ctx, fasthttp.StatusOK, 200, "成功", map[string]interface{}{
		"token":       newToken,
		"expiredTime": expiredSec,
	})
}

func (s *Server) parseJSONBody(ctx *fasthttp.RequestCtx) (*fastjson.Value, bool) {
	body := ctx.PostBody()
	if len(body) == 0 {
		return nil, false
	}

	var p fastjson.Parser
	v, err := p.ParseBytes(body)
	if err != nil {
		return nil, false
	}
	return v, true
}

func (s *Server) parseAndValidateToken(token string, deviceSecret string) (tokenPayload, bool, bool) {
	firstDot := strings.IndexByte(token, '.')
	if firstDot > 0 {
		secondRel := strings.IndexByte(token[firstDot+1:], '.')
		if secondRel > 0 {
			secondDot := firstDot + 1 + secondRel
			thirdRel := strings.IndexByte(token[secondDot+1:], '.')
			if thirdRel > 0 {
				thirdDot := secondDot + 1 + thirdRel
				kind := token[:firstDot]
				deviceID := token[firstDot+1 : secondDot]
				expiredText := token[secondDot+1 : thirdDot]
				signature := token[thirdDot+1:]

				expiredSec, err := strconv.ParseInt(expiredText, 10, 64)
				if err == nil {
					expected := md5HexParts(kind, ".", deviceID, ".", expiredText, ".", deviceSecret)
					if strings.EqualFold(expected, signature) {
						payload := tokenPayload{
							Kind:       kind,
							DeviceID:   deviceID,
							ExpiredSec: expiredSec,
							Signature:  signature,
						}
						if time.Now().Unix() > payload.ExpiredSec {
							return payload, true, true
						}
						return payload, true, false
					}
				}
			}
		}
	}

	return parseJWTToken(token, deviceSecret)
}

func parseJWTToken(token string, deviceSecret string) (tokenPayload, bool, bool) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return tokenPayload{}, false, false
	}

	signingInput := parts[0] + "." + parts[1]
	mac := hmac.New(sha256.New, []byte(deviceSecret))
	_, _ = mac.Write([]byte(signingInput))
	expectedSignature := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))
	if !hmac.Equal([]byte(expectedSignature), []byte(parts[2])) {
		return tokenPayload{}, false, false
	}

	payloadBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return tokenPayload{}, false, false
	}

	var jwtPayload struct {
		DeviceID    string `json:"deviceId"`
		ExpiredTime int64  `json:"expiredTime"`
	}
	if err := json.Unmarshal(payloadBytes, &jwtPayload); err != nil {
		return tokenPayload{}, false, false
	}

	payload := tokenPayload{
		Kind:       "jwt",
		DeviceID:   jwtPayload.DeviceID,
		ExpiredSec: jwtPayload.ExpiredTime,
		Signature:  parts[2],
	}

	if time.Now().Unix() > payload.ExpiredSec {
		return payload, true, true
	}
	return payload, true, false
}

func (s *Server) makeToken(kind string, deviceID string, deviceSecret string, expiredSec int64) string {
	expiredText := strconv.FormatInt(expiredSec, 10)
	signature := md5HexParts(kind, ".", deviceID, ".", expiredText, ".", deviceSecret)
	return kind + "." + deviceID + "." + expiredText + "." + signature
}

func encodeCompactRecord(timeValue int64, high int, low int, receivedTime int64) string {
	buf := make([]byte, 0, 48)
	buf = strconv.AppendInt(buf, timeValue, 10)
	buf = append(buf, '|')
	buf = strconv.AppendInt(buf, int64(high), 10)
	buf = append(buf, '|')
	buf = strconv.AppendInt(buf, int64(low), 10)
	buf = append(buf, '|')
	buf = strconv.AppendInt(buf, receivedTime, 10)
	return string(buf)
}

func loadDeviceSecrets(csvPath string) (map[string]string, error) {
	file, err := os.Open(csvPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	startedAt := time.Now()
	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 1024), 1024*1024)

	deviceSecrets := make(map[string]string, 1_100_000)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		deviceID, secret, ok := parseDeviceSecretLine(line)
		if !ok {
			if lineNo == 1 {
				continue
			}
			return nil, fmt.Errorf("invalid device csv line %d", lineNo)
		}
		deviceSecrets[deviceID] = secret
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	if len(deviceSecrets) == 0 {
		return nil, fmt.Errorf("no device secrets loaded from %s", csvPath)
	}

	log.Printf("loaded %d device secrets from %s in %s", len(deviceSecrets), csvPath, time.Since(startedAt))
	return deviceSecrets, nil
}

func parseDeviceSecretLine(line string) (string, string, bool) {
	parts := strings.SplitN(line, ",", 3)
	if len(parts) < 2 {
		return "", "", false
	}

	deviceID := trimCSVField(parts[0])
	secret := trimCSVField(parts[1])
	if deviceID == "" || secret == "" {
		return "", "", false
	}
	if strings.EqualFold(deviceID, "deviceId") || strings.EqualFold(deviceID, "serialNumber") {
		return "", "", false
	}
	return deviceID, secret, true
}

func trimCSVField(field string) string {
	return strings.Trim(strings.TrimSpace(field), "\"")
}

func (s *Server) writeJSON(ctx *fasthttp.RequestCtx, httpStatus int, code int, message string, data interface{}) {
	ctx.Response.Header.SetContentType("application/json; charset=utf-8")
	ctx.SetStatusCode(httpStatus)
	resp := responseEnvelope{
		Code:    code,
		Message: message,
		Data:    data,
	}
	encoded, err := json.Marshal(resp)
	if err != nil {
		ctx.SetStatusCode(fasthttp.StatusInternalServerError)
		_, _ = ctx.WriteString(`{"code":500,"message":"服务端异常","data":null}`)
		return
	}
	_, _ = ctx.Write(encoded)
}

func randomToken(byteLen int) (string, error) {
	raw := make([]byte, byteLen)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(raw), nil
}

func md5Hex(input string) string {
	sum := md5.Sum([]byte(input))
	return hex.EncodeToString(sum[:])
}

func md5HexParts(parts ...string) string {
	hasher := md5.New()
	for _, part := range parts {
		_, _ = hasher.Write([]byte(part))
	}
	return hex.EncodeToString(hasher.Sum(nil))
}

func getEnv(key, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}

func getEnvInt(key string, fallback int) int {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func getEnvBool(key string, fallback bool) bool {
	value := strings.TrimSpace(strings.ToLower(os.Getenv(key)))
	if value == "" {
		return fallback
	}
	switch value {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
}
