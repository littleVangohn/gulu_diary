local body_file = os.getenv("WRK_BODY_FILE")
if not body_file or body_file == "" then
  error("WRK_BODY_FILE is required")
end

local f = assert(io.open(body_file, "r"))
wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"
wrk.body = f:read("*all")
f:close()

local counts = {}

response = function(status, headers, body)
  counts[status] = (counts[status] or 0) + 1
end

done = function(summary, latency, requests)
  for code, count in pairs(counts) do
    io.write(string.format("STATUS %d %d\n", code, count))
  end
end
