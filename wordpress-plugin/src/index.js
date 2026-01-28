/**
 * Placeholder components - to be fully implemented
 */
import React from 'react';

export const Navigation = ({ user, onLogout }) => (
  <nav className="absenzflow-nav">
    <ul>
      <li><a href="/">Dashboard</a></li>
      <li><a href="/create">Abwesenheit melden</a></li>
      <li><a href="/absences">Meine Abwesenheiten</a></li>
      {(user?.role === 'substitution_planner' || user?.role === 'admin') && (
        <li><a href="/planner">Vertretungsplanung</a></li>
      )}
      <li className="nav-user">
        {user?.display_name}
        <button onClick={onLogout} className="btn btn-secondary" style={{marginLeft: '10px'}}>
          Abmelden
        </button>
      </li>
    </ul>
  </nav>
);

export const LoginForm = ({ onLogin }) => {
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    const result = await onLogin(username, password);
    
    if (!result.success) {
      setError(result.error);
    }
    
    setLoading(false);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="alert alert-error">{error}</div>}
      
      <div className="form-group">
        <label>Benutzername</label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          disabled={loading}
        />
      </div>
      
      <div className="form-group">
        <label>Passwort</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={loading}
        />
      </div>
      
      <button type="submit" className="btn btn-primary" disabled={loading} style={{width: '100%'}}>
        {loading ? 'Anmelden...' : 'Anmelden'}
      </button>
    </form>
  );
};

export default { Navigation, LoginForm };
