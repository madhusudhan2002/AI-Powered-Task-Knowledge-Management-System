import { useState } from "react";
import api from "../api/axios";
export default function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/search", { params: { q: query, top_k: 5 } });
      setResults(res.data.results);
      setSearched(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Search failed");
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="container">
      <div className="card">
        <h3>AI-Powered Semantic Search</h3>
        <form onSubmit={handleSearch} className="row">
          <input
            placeholder="Ask a question about your documents..."
            value={query} onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </form>
        {error && <div className="error">{error}</div>}
      </div>
      <div className="card">
        {results.map((r, i) => (
          <div className="result-item" key={i}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>{r.filename}</strong>
              <span className="score-tag">similarity: {r.score}</span>
            </div>
            <p style={{ margin: "6px 0" }}>{r.chunk_text}</p>
          </div>
        ))}
        {searched && results.length === 0 && (
          <p style={{ color: "#889" }}>No relevant results found.</p>
        )}
        {!searched && (
          <p style={{ color: "#889" }}>Results will appear here after you search.</p>
        )}
      </div>
    </div>
  );
}