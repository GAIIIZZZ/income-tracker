const path = require("path");
const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const app = express();

app.use(
  "/api",
  createProxyMiddleware({ target: BACKEND_URL, changeOrigin: true, pathRewrite: { "^/": "/api/" } })
);
app.use(
  "/images",
  createProxyMiddleware({ target: BACKEND_URL, changeOrigin: true, pathRewrite: { "^/": "/images/" } })
);

app.use(express.static(path.join(__dirname, "public")));

app.listen(PORT, () => {
  console.log(`Frontend running at http://localhost:${PORT}`);
  console.log(`Proxying /api and /images to ${BACKEND_URL}`);
});
