import { Routes, Route, Navigate } from 'react-router-dom';
import RequireAuth from './components/RequireAuth';
import Layout from './components/Layout';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Knowledge from './pages/Knowledge';
import Audit from './pages/Audit';
import { getAccessToken } from './auth';

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={getAccessToken() ? <Navigate to="/chat" replace /> : <Login />}
      />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<Chat />} />
        <Route path="kb" element={<Knowledge />} />
        <Route path="audit" element={<Audit />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
