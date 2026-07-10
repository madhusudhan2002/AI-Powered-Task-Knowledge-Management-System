import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import PrivateRoute from "./components/PrivateRoute";
import Navbar from "./components/Navbar";
import Login from "./pages/Login";
import Tasks from "./pages/Tasks";
import Documents from "./pages/Documents";
import Search from "./pages/Search";
import Analytics from "./pages/Analytics";
function Layout({ children }) {
  return (
    <>
      <Navbar />
      {children}
    </>
  );
}
function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={
        <PrivateRoute><Layout><Tasks /></Layout></PrivateRoute>
      } />
      <Route path="/documents" element={
        <PrivateRoute><Layout><Documents /></Layout></PrivateRoute>
      } />
      <Route path="/search" element={
        <PrivateRoute><Layout><Search /></Layout></PrivateRoute>
      } />
      <Route path="/analytics" element={
        <PrivateRoute><Layout><Analytics /></Layout></PrivateRoute>
      } />
    </Routes>
  );
}
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}