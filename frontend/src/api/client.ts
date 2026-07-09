/**
 * Shared Axios client for communicating with the FastAPI backend.
 * - Uses a common base URL for all API requests.
 * - Automatically attaches the JWT access token from localStorage
 *   to the Authorization header before every request.
 * - Intercepts 401 (Unauthorized) responses, clears stored auth data,
 *   and redirects the user to the login page.
 */
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_email");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;