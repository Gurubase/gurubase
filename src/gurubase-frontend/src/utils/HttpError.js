class HttpError extends Error {
  constructor(message, status, type = "openai", reason = "openai_key_invalid") {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.type = type;
    this.reason = reason;
  }
}

export default HttpError;
