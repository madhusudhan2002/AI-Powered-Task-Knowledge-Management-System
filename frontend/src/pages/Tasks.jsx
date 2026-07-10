import { useEffect, useState } from "react";
import api from "../api/axios";
import { useAuth } from "../context/AuthContext";
export default function Tasks() {
  const { user } = useAuth();
  const isAdmin = user.role === "admin";
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [assignedFilter, setAssignedFilter] = useState("");
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assignTo, setAssignTo] = useState("");
  async function loadTasks() {
    setError("");
    try {
      const params = {};
      if (statusFilter) params.status_filter = statusFilter;
      if (assignedFilter) params.assigned_to = assignedFilter;
      const res = await api.get("/tasks", { params });
      setTasks(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load tasks");
    }
  }
  async function loadUsers() {
    if (!isAdmin) return;
    try {
      const res = await api.get("/users");
      setUsers(res.data);
    } catch {
      // ignore
    }
  }
  useEffect(() => {
    loadUsers();
  }, []);
  useEffect(() => {
    loadTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, assignedFilter]);
  async function handleCreate(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/tasks", {
        title,
        description,
        assigned_to: assignTo ? Number(assignTo) : null,
      });
      setTitle(""); setDescription(""); setAssignTo("");
      loadTasks();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create task");
    }
  }
  async function toggleStatus(task) {
    const newStatus = task.status === "pending" ? "completed" : "pending";
    try {
      await api.patch(`/tasks/${task.id}`, { status: newStatus });
      loadTasks();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update task");
    }
  }
  return (
    <div className="container">
      {isAdmin && (
        <div className="card">
          <h3>Create Task</h3>
          <form onSubmit={handleCreate}>
            <div className="row" style={{ marginBottom: 8 }}>
              <input placeholder="Title" value={title} required
                onChange={(e) => setTitle(e.target.value)} style={{ flex: 2 }} />
              <input placeholder="Description" value={description}
                onChange={(e) => setDescription(e.target.value)} style={{ flex: 3 }} />
              <select value={assignTo} onChange={(e) => setAssignTo(e.target.value)}>
                <option value="">Assign to...</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
                ))}
              </select>
              <button type="submit">Create</button>
            </div>
          </form>
        </div>
      )}
      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <h3 style={{ marginRight: "auto" }}>Tasks</h3>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
          </select>
          {isAdmin && (
            <select value={assignedFilter} onChange={(e) => setAssignedFilter(e.target.value)}>
              <option value="">All users</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          )}
        </div>
        {error && <div className="error">{error}</div>}
        <table>
          <thead>
            <tr>
              <th>Title</th><th>Description</th><th>Status</th><th>Assigned To</th><th></th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td>{t.title}</td>
                <td>{t.description}</td>
                <td><span className={`badge ${t.status}`}>{t.status}</span></td>
                <td>{t.assigned_to ?? "-"}</td>
                <td>
                  <button className="secondary" onClick={() => toggleStatus(t)}>
                    Mark {t.status === "pending" ? "Completed" : "Pending"}
                  </button>
                </td>
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr><td colSpan="5" style={{ color: "#889" }}>No tasks found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}