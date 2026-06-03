(function () {
    function toastManager() {
        return {
            toasts: [],
            addToast(detail) {
                const id = Date.now();
                this.toasts.push({
                    id,
                    message: detail.message,
                    type: detail.type || "info",
                    visible: true,
                });

                setTimeout(() => {
                    this.removeToast(id);
                }, detail.duration || 5000);
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

    function showToast(message, type = "info", duration = 5000) {
        window.dispatchEvent(
            new CustomEvent("show-toast", {
                detail: { message, type, duration },
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

    function extractErrorMessage(payload, fallback) {
        if (!payload) return fallback;
        if (typeof payload === "string") return payload.trim() || fallback;

        const directMessage =
            payload.error ||
            payload.detail ||
            payload.message ||
            payload.non_field_errors;
        const directValues = flattenErrorValues(directMessage);
        if (directValues.length) return directValues.join("; ");

        if (payload.errors) {
            const errorValues = flattenErrorValues(payload.errors);
            if (errorValues.length) return errorValues.join("; ");
        }

        const payloadValues = flattenErrorValues(payload);
        return payloadValues.length ? payloadValues.join("; ") : fallback;
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

        const message = extractErrorMessage(payload, defaultMessage);
        const statusPrefix = response.status ? `${response.status}: ` : "";
        return new Error(message === defaultMessage ? statusPrefix + message : message);
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
        delete(endpoint) {
            return apiRequest("DELETE", endpoint);
        },
    };

    window.toastManager = toastManager;
    window.showToast = showToast;
    window.getCookie = getCookie;
    window.extractErrorMessage = extractErrorMessage;
    window.parseApiError = parseApiError;
    window.API = API;
})();
