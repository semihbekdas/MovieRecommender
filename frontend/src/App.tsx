import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, AuthContext } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import MovieDetail from './pages/MovieDetail';
import Profile from './pages/Profile';
import UserProfile from './pages/UserProfile';
import { useContext, type ReactNode } from 'react';

const PrivateRoute = ({ children }: { children: ReactNode }) => {
  const { user, isAuthenticated } = useContext(AuthContext);
  return isAuthenticated ? children : <Navigate to='/login' />;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className='min-h-screen bg-gray-900 text-white'>
          <Navbar />
          <Routes>
            <Route path='/login' element={<Login />} />
            <Route path='/register' element={<Register />} />
            <Route path='/' element={
              <PrivateRoute>
                <Home />
              </PrivateRoute>
            } />
            <Route path='/movie/:id' element={
              <PrivateRoute>
                <MovieDetail />
              </PrivateRoute>
            } />
            <Route path='/profile' element={
              <PrivateRoute>
                <Profile />
              </PrivateRoute>
            } />
            <Route path='/profile/:username' element={
              <PrivateRoute>
                <UserProfile />
              </PrivateRoute>
            } />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
