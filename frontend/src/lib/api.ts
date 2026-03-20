import axios from 'axios';

const normalizeApiBaseUrl = (url: string) => {
    const trimmed = url.replace(/\/+$/, '');

    if (trimmed.endsWith('/api/v1')) {
        return trimmed;
    }

    if (trimmed.endsWith('/api')) {
        return `${trimmed}/v1`;
    }

    return `${trimmed}/api/v1`;
};

const envApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
const baseURL = envApiUrl
    ? normalizeApiBaseUrl(envApiUrl)
    : (process.env.NODE_ENV === 'development' ? 'http://localhost:8000/api/v1' : '/api/v1');

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
