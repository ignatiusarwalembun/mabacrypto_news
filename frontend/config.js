(function () {
  "use strict";

  const isLocal = ["localhost", "127.0.0.1", "0.0.0.0"].includes(window.location.hostname);
  const PRODUCTION_API_BASE_URL = "https://mabacryptonews-production-d8d7.up.railway.app/api";
  const LOCAL_API_BASE_URL = "http://localhost:5000/api";

  // Production uses this shared config file on every browser/device.
  // localStorage is only an optional override for debugging, never the production source of truth.
  const override = localStorage.getItem("mabacrypto_api_override");

  window.APP_CONFIG = Object.freeze({
    API_BASE_URL: override || (isLocal ? LOCAL_API_BASE_URL : PRODUCTION_API_BASE_URL),
    PRODUCTION_API_BASE_URL,
    LOCAL_API_BASE_URL,
    APP_NAME: "MabaCrypto News"
  });
})();
