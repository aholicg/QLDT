import axios from "axios";

export type UserRole = "ADMIN" | "LECTURER" | "STUDENT";

export interface AuthUser {
  userId: number | string;
  username: string;
  fullName: string;
  email: string | null;
  role: UserRole;
  studentCode: string | null;
  lecturerCode: string | null;
}

export interface ApiErrorBody {
  status: number;
  error: string;
  message: string;
  details: Array<{ field?: string; message?: string }>;
  path: string;
  timestamp: string;
}

export function requireItems<T>(payload: unknown): T[] {
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("items" in payload) ||
    !Array.isArray(payload.items)
  ) {
    throw new Error("Invalid API list response: expected an items array.");
  }
  return payload.items as T[];
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("qldt.token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      window.dispatchEvent(new Event("qldt:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export function readApiError(error: unknown): ApiErrorBody | undefined {
  if (!axios.isAxiosError<ApiErrorBody>(error)) return undefined;
  return error.response?.data;
}

export async function signIn(username: string, password: string): Promise<AuthUser> {
  const response = await api.post<{ accessToken: string; user: AuthUser }>(
    "/auth/login",
    { username, password },
  );
  sessionStorage.setItem("qldt.token", response.data.accessToken);
  return response.data.user;
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const response = await api.get<{ user: AuthUser }>("/auth/me");
  return response.data.user;
}

export function clearSession() {
  sessionStorage.removeItem("qldt.token");
}

export function hasSession() {
  return Boolean(sessionStorage.getItem("qldt.token"));
}

export default api;
