wrk.method = "POST"
wrk.headers["Content-Type"] = "application/json"

local bodies = {}
local idx = 1
local counts = {}
local body_path = os.getenv("WRK_BODY_POOL_FILE")

init = function(args)
  if not body_path or body_path == "" then
    error("WRK_BODY_POOL_FILE is required")
  end

  for line in io.lines(body_path) do
    if line and line ~= "" then
      bodies[#bodies + 1] = line
    end
  end

  if #bodies == 0 then
    error("no request bodies loaded from " .. body_path)
  end

  io.write(string.format("loaded bodies: %d from %s\n", #bodies, body_path))
end

request = function()
  local body = bodies[idx]
  idx = idx + 1
  if idx > #bodies then
    idx = 1
  end
  return wrk.format(nil, nil, nil, body)
end

response = function(status, headers, body)
  counts[status] = (counts[status] or 0) + 1
end

done = function(summary, latency, requests)
  for code, count in pairs(counts) do
    io.write(string.format("STATUS %d %d\n", code, count))
  end
end
