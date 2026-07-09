/**
 * Authentication API wrapper.
 * Provides typed helper functions for user registration and login
 * using the shared Axios client, returning only the response data.
 */

import api from "./client";

import type { RegisterPayload, LoginPayload, TokenResponse, UserResponse } from "../types/api";

export const registerUser = (payload: RegisterPayload) =>
  api.post<UserResponse>("/register", payload).then((res) => res.data);

export const loginUser = (payload: LoginPayload) =>
  api.post<TokenResponse>("/login", payload).then((res) => res.data);

