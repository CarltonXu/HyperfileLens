export function getApiErrorMessage(
  error: unknown,
  fallback = "An unexpected error occurred",
): string {
  const err = error as {
    message?: string;
    response?: {
      data?: unknown;
    };
  };

  const data = err.response?.data;
  if (typeof data === "string" && data.trim()) {
    return data;
  }

  if (data && typeof data === "object") {
    const record = data as Record<string, unknown>;
    for (const key of ["detail", "error", "message", "non_field_errors"]) {
      const value = record[key];
      if (typeof value === "string" && value.trim()) {
        return value;
      }
      if (Array.isArray(value) && value.length > 0) {
        return value.map(String).join(", ");
      }
    }

    const firstFieldError = Object.values(record).find(
      (value) =>
        typeof value === "string" || (Array.isArray(value) && value.length > 0),
    );
    if (typeof firstFieldError === "string") {
      return firstFieldError;
    }
    if (Array.isArray(firstFieldError)) {
      return firstFieldError.map(String).join(", ");
    }
  }

  return err.message || fallback;
}
