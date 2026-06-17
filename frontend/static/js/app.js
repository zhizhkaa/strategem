(function () {
    const MAX_INLINE_ERRORS = 3;

    function toastManager() {
        return {
            toasts: [],
            detailModal: null,
            addToast(detail) {
                const id = Date.now();
                this.toasts.push({
                    id,
                    message: detail.message,
                    type: detail.type || "info",
                    details: detail.details || [],
                    detailsTitle: detail.detailsTitle || "Подробности",
                    visible: true,
                });

                setTimeout(() => {
                    this.removeToast(id);
                }, detail.duration || 5000);
            },
            openDetails(toast) {
                this.detailModal = {
                    title: toast.detailsTitle || "Подробности",
                    items: toast.details || [],
                };
            },
            closeDetails() {
                this.detailModal = null;
            },
            removeToast(id) {
                const toast = this.toasts.find((t) => t.id === id);
                if (toast) {
                    toast.visible = false;
                    setTimeout(() => {
                        this.toasts = this.toasts.filter((t) => t.id !== id);
                    }, 300);
                }
            },
        };
    }

    function normalizeToastDetail(message, type, duration) {
        if (message && typeof message === "object") {
            const details = message.details || message.apiErrorDetails || [];
            return {
                message: message.message || "Ошибка",
                type: message.type || type || "info",
                duration: message.duration || duration || 5000,
                details: Array.isArray(details) ? details : [],
                detailsTitle:
                    message.detailsTitle ||
                    message.apiErrorDetailsTitle ||
                    "Подробности",
            };
        }

        return {
            message,
            type: type || "info",
            duration: duration || 5000,
            details: [],
            detailsTitle: "Подробности",
        };
    }

    function showToast(message, type = "info", duration = 5000) {
        const detail = normalizeToastDetail(message, type, duration);
        window.dispatchEvent(
            new CustomEvent("show-toast", {
                detail,
            }),
        );
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(
                        cookie.substring(name.length + 1),
                    );
                    break;
                }
            }
        }
        return cookieValue;
    }

    function flattenErrorValues(value) {
        if (value === null || value === undefined || value === "") return [];
        if (typeof value === "string") return [value];
        if (typeof value === "number" || typeof value === "boolean") {
            return [String(value)];
        }
        if (Array.isArray(value)) {
            return value.flatMap((item) => flattenErrorValues(item));
        }
        if (typeof value === "object") {
            return Object.entries(value).flatMap(([field, fieldValue]) => {
                const messages = flattenErrorValues(fieldValue);
                if (!messages.length) return [];
                if (field === "non_field_errors" || field === "detail") {
                    return messages;
                }
                return messages.map((message) => `${field}: ${message}`);
            });
        }
        return [];
    }

    function uniqueValues(values) {
        const seen = new Set();
        const result = [];
        for (const value of values) {
            if (seen.has(value)) continue;
            seen.add(value);
            result.push(value);
        }
        return result;
    }

    function flattenFieldErrors(errors) {
        if (!errors || typeof errors !== "object" || Array.isArray(errors)) {
            return flattenErrorValues(errors);
        }

        const groupedByMessage = new Map();
        const directMessages = [];

        for (const [field, fieldValue] of Object.entries(errors)) {
            const messages = uniqueValues(flattenErrorValues(fieldValue));
            if (!messages.length) continue;
            if (field === "non_field_errors" || field === "detail") {
                directMessages.push(...messages);
                continue;
            }
            for (const message of messages) {
                if (!groupedByMessage.has(message)) {
                    groupedByMessage.set(message, []);
                }
                groupedByMessage.get(message).push(field);
            }
        }

        const fieldMessages = [];
        for (const [message, fields] of groupedByMessage.entries()) {
            fieldMessages.push(fields.length > 1 ? message : `${fields[0]}: ${message}`);
        }

        return uniqueValues([...directMessages, ...fieldMessages]);
    }

    function pluralizeErrorCount(count) {
        const mod10 = count % 10;
        const mod100 = count % 100;
        if (mod10 === 1 && mod100 !== 11) return "ошибка";
        if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
            return "ошибки";
        }
        return "ошибок";
    }

    function summarizeErrorValues(values, fallback) {
        if (!values.length) {
            return { message: fallback, details: [] };
        }

        if (values.length <= MAX_INLINE_ERRORS) {
            return { message: values.join("\n"), details: [] };
        }

        const hiddenCount = values.length - MAX_INLINE_ERRORS;
        const suffix = `ещё ${hiddenCount} ${pluralizeErrorCount(hiddenCount)}`;
        return {
            message: `${values.slice(0, MAX_INLINE_ERRORS).join("\n")}\n${suffix}`,
            details: values,
        };
    }

    function formatErrorPayload(payload, fallback) {
        if (!payload) return { message: fallback, details: [] };
        if (typeof payload === "string") {
            return { message: payload.trim() || fallback, details: [] };
        }

        const directMessage =
            payload.error ||
            payload.detail ||
            payload.message ||
            payload.non_field_errors;
        const directValues = flattenErrorValues(directMessage);
        if (directValues.length) return summarizeErrorValues(directValues, fallback);

        if (payload.errors) {
            const errorValues = flattenFieldErrors(payload.errors);
            if (errorValues.length) return summarizeErrorValues(errorValues, fallback);
        }

        const payloadValues = flattenErrorValues(payload);
        return summarizeErrorValues(payloadValues, fallback);
    }

    function extractErrorMessage(payload, fallback) {
        return formatErrorPayload(payload, fallback).message;
    }

    async function parseApiError(response, fallback) {
        const defaultMessage = fallback || "Ошибка запроса. Попробуйте ещё раз";
        let payload = null;

        try {
            const contentType = response.headers.get("content-type") || "";
            if (contentType.includes("application/json")) {
                payload = await response.json();
            } else {
                payload = await response.text();
            }
        } catch (_) {
            payload = null;
        }

        const formatted = formatErrorPayload(payload, defaultMessage);
        const message = formatted.message;
        const statusPrefix = response.status ? `${response.status}: ` : "";
        const error = new Error(
            message === defaultMessage ? statusPrefix + message : message,
        );
        error.apiErrorPayload = payload;
        error.apiErrorDetails = formatted.details;
        error.apiErrorDetailsTitle = "Ошибки в решениях";
        return error;
    }

    async function parseResponse(response) {
        if (response.status === 204) return null;

        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            return response.json();
        }

        const text = await response.text();
        return text || null;
    }

    async function apiRequest(method, endpoint, data) {
        const headers = {};
        const options = {
            method,
            headers,
            credentials: "include",
        };

        if (method !== "GET") {
            headers["X-CSRFToken"] = getCookie("csrftoken");
        }
        if (data !== undefined) {
            headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(data);
        }

        const response = await fetch(API.baseUrl + endpoint, options);
        if (!response.ok) {
            throw await parseApiError(response);
        }
        return parseResponse(response);
    }

    const API = {
        baseUrl: "/api",
        getCSRFToken() {
            return getCookie("csrftoken");
        },
        get(endpoint) {
            return apiRequest("GET", endpoint);
        },
        post(endpoint, data = {}) {
            return apiRequest("POST", endpoint, data);
        },
        patch(endpoint, data = {}) {
            return apiRequest("PATCH", endpoint, data);
        },
        delete(endpoint) {
            return apiRequest("DELETE", endpoint);
        },
    };

    window.toastManager = toastManager;
    window.showToast = showToast;
    window.getCookie = getCookie;
    window.extractErrorMessage = extractErrorMessage;
    window.formatErrorPayload = formatErrorPayload;
    window.parseApiError = parseApiError;
    window.API = API;
})();
