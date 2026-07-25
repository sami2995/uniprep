import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { getDefaultPathForRole, roleCanAccess } from "./roleRoutes";

const ProtectedRoute = ({ children, role, roles }) => {
  const { user, loading } = useAuth();
  const allowedRoles = roles || (role ? [role] : []);

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <p>Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!roleCanAccess(user.role, allowedRoles)) {
    return <Navigate to={getDefaultPathForRole(user.role)} replace />;
  }

  return children;
};

export default ProtectedRoute;
