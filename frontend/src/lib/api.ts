import axios from 'axios';

// Use env override for local dev or Docker; fall back to localhost API.
const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
    baseURL: baseURL,
});

// Add request interceptor to set proper content type
api.interceptors.request.use((config) => {
    // If data is FormData, let axios handle the content type
    if (!(config.data instanceof FormData)) {
        config.headers['Content-Type'] = 'application/json';
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

export default api;
