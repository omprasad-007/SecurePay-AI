export function validateUploadFile(file) {
  if (!file) return "No file selected";
  const name = file.name.toLowerCase();
  const allowed = name.endsWith(".csv") || name.endsWith(".xlsx");
  if (!allowed) return "Only .csv and .xlsx files are allowed";
  if (file.size > 5 * 1024 * 1024) return "File exceeds 5MB limit";
  const forbidden = [".exe", ".bat", ".cmd", ".sh", ".ps1"];
  if (forbidden.some((ext) => name.endsWith(ext))) return "Executable files are not allowed";
  return null;
}

export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      const base64 = result.includes(",") ? result.split(",")[1] : result;
      resolve(base64);
    };
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}
