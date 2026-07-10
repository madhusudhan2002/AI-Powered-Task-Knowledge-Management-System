import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";
export default function Documents() {
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const [docs, setDocs] = useState([]);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  async function loadDocs() {
    const res = await api.get("/documents");
    setDocs(res.data);
  }
  useEffect(() => { loadDocs(); }, []);
  async function handleUpload(e) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post("/documents/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFile(null);
      loadDocs();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  }
  return (
    <div className="container">
      {isAdmin && (
        <div className="card">
          <h3>Upload Document (.txt / .pdf)</h3>
          <form onSubmit={handleUpload} className="row">
            <input type="file" accept=".txt,.pdf" onChange={(e) => setFile(e.target.files[0])} />
            <button type="submit" disabled={uploading || !file}>
              {uploading ? "Uploading & indexing..." : "Upload"}
            </button>
          </form>
          {error && <div className="error">{error}</div>}
        </div>
      )}
      <div className="card">
        <h3>Knowledge Base</h3>
        <table>
          <thead>
            <tr><th>Filename</th><th>Type</th><th>Chunks Indexed</th><th>Uploaded At</th></tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>{d.filename}</td>
                <td>{d.file_type}</td>
                <td>{d.is_indexed ? d.chunk_count : "indexing..."}</td>
                <td>{new Date(d.uploaded_at).toLocaleString()}</td>
              </tr>
            ))}
            {docs.length === 0 && (
              <tr><td colSpan="4" style={{ color: "#889" }}>No documents uploaded yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}