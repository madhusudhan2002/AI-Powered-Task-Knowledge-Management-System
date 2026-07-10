import { useEffect, useState } from "react";
import api from "../api/axios";
export default function Analytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.get("/analytics")
      .then((res) => setData(res.data))
      .catch((err) => setError(err.response?.data?.detail || "Failed to load analytics"));
  }, []);
  if (error) return <div className="container"><div className="error">{error}</div></div>;
  if (!data) return <div className="container">Loading...</div>;
  return (
    <div className="container">
      <div className="stat-grid" style={{ marginBottom: 16 }}>
        <div className="stat-box"><div className="num">{data.total_tasks}</div>Total Tasks</div>
        <div className="stat-box"><div className="num">{data.completed_tasks}</div>Completed</div>
        <div className="stat-box"><div className="num">{data.pending_tasks}</div>Pending</div>
        <div className="stat-box"><div className="num">{data.total_documents}</div>Documents</div>
        <div className="stat-box"><div className="num">{data.total_users}</div>Users</div>
      </div>
      <div className="card">
        <h3>Most Searched Queries</h3>
        <table>
          <thead><tr><th>Query</th><th>Count</th></tr></thead>
          <tbody>
            {data.top_search_queries.map((q, i) => (
              <tr key={i}><td>{q.query_text}</td><td>{q.count}</td></tr>
            ))}
            {data.top_search_queries.length === 0 && (
              <tr><td colSpan="2" style={{ color: "#889" }}>No searches yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}