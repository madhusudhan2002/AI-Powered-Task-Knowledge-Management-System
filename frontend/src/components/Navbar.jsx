import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  function handleLogout() {
    logout();
    navigate("/login");
  }
  return (
    <div className="navbar">
      <div className="row">
        <strong style={{ marginRight: 20 }}>Task & Knowledge System</strong>
        <NavLink to="/" end>Tasks</NavLink>
        <NavLink to="/documents">Documents</NavLink>
        <NavLink to="/search">Search</NavLink>
        <NavLink to="/analytics">Analytics</NavLink>
      </div>
      <div className="row">
        <span>{user.name} ({user.role})</span>
        <button className="secondary" onClick={handleLogout}>Logout</button>
      </div>
    </div>
  );
}