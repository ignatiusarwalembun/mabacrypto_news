// Local/LAN API resolver.
// Desktop localhost  -> http://localhost:5000/api
// Phone on same Wi-Fi -> http://<PC-IP>:5000/api
const currentHost = window.location.hostname || "localhost";
const currentProtocol = window.location.protocol === "https:" ? "http:" : "http:";

window.APP_CONFIG = {
  API_BASE_URL: `${currentProtocol}//${currentHost}:5000/api`
};
