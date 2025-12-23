import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: __ENV.VUS ? parseInt(__ENV.VUS) : 10,
  duration: __ENV.DURATION || "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000", "p(99)<5000"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const TOKEN = __ENV.TOKEN || "";
const PATH = __ENV.PATH || "/app/api/v1/chat/turn"; // ✅ burayı doğru ayarla

export default function () {
  const payload = JSON.stringify({
    mode: "review",
    topic: "security_policy",
    level: "beginner",
    message:
      "SORU: SQL Injection nedir?\nCEVAP: Kullanıcı girdisi filtrelenmeden sorguya eklenirse saldırgan sorguyu manipüle edebilir.",
    history: [],
  });

  const res = http.post(`${BASE}${PATH}`, payload, {
    headers: {
      "Content-Type": "application/json",
      ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
    },
  });

  check(res, { "status 200": (r) => r.status === 200 });
  sleep(1);
}
