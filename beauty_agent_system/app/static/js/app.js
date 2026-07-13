// Auto-refresh the System Health page every 30s so the sleep/active status
// stays current without the founder needing to reload manually.
if (window.location.pathname.startsWith("/admin/system-health")) {
  setInterval(() => window.location.reload(), 30000);
}
