import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_URL;
console.log("API BASE URL:", baseURL);

if (!baseURL) {
  throw new Error("NEXT_PUBLIC_API_URL is not set. API requests cannot be routed.");
}

const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export default api;
