/**
 * TraceLens API Client
 */
const api = {
  baseUrl: "/api",

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        let errMessage = `HTTP ${res.status}`;
        try {
          const errData = await res.json();
          if (errData && errData.detail) {
            errMessage = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
          }
        } catch (_) {}
        throw new Error(errMessage);
      }
      return await res.json();
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  getHealth() {
    return this.request("/health");
  },

  getReference() {
    return this.request("/reference/event-types");
  },

  getTraces() {
    return this.request("/traces");
  },

  getTrace(traceId) {
    return this.request(`/traces/${encodeURIComponent(traceId)}`);
  },

  deleteTrace(traceId) {
    return this.request(`/traces/${encodeURIComponent(traceId)}`, {
      method: "DELETE"
    });
  },

  generateTrace(params = {}) {
    return this.request("/traces/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params)
    });
  },

  uploadTrace(file) {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("/traces/upload", {
      method: "POST",
      body: formData
    });
  },

  getEvents(traceId, { threadId, eventClass, limit = 200, offset = 0 } = {}) {
    const params = new URLSearchParams({ limit, offset });
    if (threadId !== undefined && threadId !== null) params.set("thread_id", threadId);
    if (eventClass) params.set("event_class", eventClass);
    return this.request(`/traces/${encodeURIComponent(traceId)}/events?${params.toString()}`);
  },

  getTimeline(traceId, startNs = null, endNs = null) {
    const params = new URLSearchParams();
    if (startNs !== null && startNs !== undefined) params.set("start_ns", startNs);
    if (endNs !== null && endNs !== undefined) params.set("end_ns", endNs);
    const q = params.toString();
    return this.request(`/traces/${encodeURIComponent(traceId)}/timeline${q ? "?" + q : ""}`);
  },

  getStats(traceId) {
    return this.request(`/traces/${encodeURIComponent(traceId)}/stats`);
  },

  getAnomalies(traceId) {
    return this.request(`/traces/${encodeURIComponent(traceId)}/anomalies`);
  }
};
