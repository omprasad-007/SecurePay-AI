const envBaseUrl = import.meta.env.VITE_API_URL?.trim();
const API_BASE_URL = (envBaseUrl ? envBaseUrl.replace(/\/+$/, "") : "") || "https://securepay-ai.onrender.com";

export default API_BASE_URL;
