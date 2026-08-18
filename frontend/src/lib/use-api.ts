"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { apiDelete, apiGet, apiPatch, apiPost, apiPostBlob } from "@/lib/api";

export function useApi() {
  const { getToken, isSignedIn } = useAuth();

  const withToken = useCallback(async () => {
    if (!isSignedIn) return null;
    return getToken();
  }, [getToken, isSignedIn]);

  const get = useCallback(
    async <T,>(path: string) => apiGet<T>(path, await withToken()),
    [withToken],
  );

  const post = useCallback(
    async <T,>(path: string, body?: unknown) => apiPost<T>(path, body, await withToken()),
    [withToken],
  );

  const patch = useCallback(
    async <T,>(path: string, body?: unknown) => apiPatch<T>(path, body, await withToken()),
    [withToken],
  );

  const del = useCallback(
    async <T,>(path: string) => apiDelete<T>(path, await withToken()),
    [withToken],
  );

  const postBlob = useCallback(
    async (path: string, body?: unknown) => apiPostBlob(path, body ?? {}, await withToken()),
    [withToken],
  );

  return { get, post, patch, del, postBlob, isSignedIn };
}
