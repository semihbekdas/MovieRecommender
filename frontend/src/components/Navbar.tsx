import { useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const Navbar = () => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-slate-900 text-white shadow-lg">
      <div className="container mx-auto px-6 py-4 flex justify-between items-center">
        <Link to="/" className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent hover:opacity-80 transition">
          MovieMind
        </Link>
        
        <div className="flex items-center space-x-6">
          {user ? (
            <>
              <Link to="/" className="hover:text-blue-400 transition font-medium">Home</Link>
              <Link to="/profile" className="hover:text-blue-400 transition font-medium">Profile</Link>
              
              <div className="flex items-center space-x-4 border-l border-gray-700 pl-6">
                <span className="text-gray-400 text-sm">Hi, {user.username}</span>
                <button 
                  onClick={handleLogout} 
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-full text-sm font-medium transition shadow-md"
                >
                  Logout
                </button>
              </div>
            </>
          ) : (
            <div className="space-x-4">
              <Link to="/login" className="hover:text-blue-400 transition font-medium">Login</Link>
              <Link 
                to="/register" 
                className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-full font-medium transition shadow-md"
              >
                Register
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
