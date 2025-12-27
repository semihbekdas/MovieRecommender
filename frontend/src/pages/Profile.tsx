import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';

interface Movie {
  id: number;
  title: string;
  posterUrl: string;
  year?: number;
  userRating?: number;
  tmdbRating?: string;
  actors?: string;
  director?: string;
}

interface User {
  id: number;
  username: string;
  firstName?: string;
  lastName?: string;
  profilePicture?: string;
  imdbProfileUrl?: string;
  Watchlist?: Movie[];
  Favorites?: Movie[];
}

interface FriendRequest {
  id: number;
  requesterId: number;
  Requester: {
    id: number;
    username: string;
    profilePicture?: string;
  };
  status: string;
}

const Profile = () => {
  const [user, setUser] = useState<User | null>(null);
  const [friends, setFriends] = useState<User[]>([]);
  const [requests, setRequests] = useState<FriendRequest[]>([]);
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [ratedMovies, setRatedMovies] = useState<Movie[]>([]);
  
  // List Search States
  const [searchRated, setSearchRated] = useState('');
  const [searchWatchlist, setSearchWatchlist] = useState('');
  const [searchFavorites, setSearchFavorites] = useState('');

  // Edit Mode State
  const [isEditing, setIsEditing] = useState(false);
  const [editFirstName, setEditFirstName] = useState('');
  const [editLastName, setEditLastName] = useState('');
  const [editProfilePicture, setEditProfilePicture] = useState('');
  const [editImdbProfileUrl, setEditImdbProfileUrl] = useState('');

  useEffect(() => {
    fetchProfile();
    fetchFriends();
    fetchRequests();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get('/users/me');
      setUser(res.data);
      setEditFirstName(res.data.firstName || '');
      setEditLastName(res.data.lastName || '');
      setEditProfilePicture(res.data.profilePicture || '');
      setEditImdbProfileUrl(res.data.imdbProfileUrl || '');

      // Process ratings
      if (res.data.Ratings && res.data.Ratings.length > 0) {
        const processedRatings = res.data.Ratings.map((r: any) => ({
          id: r.Movie.id,
          title: r.Movie.title,
          year: r.Movie.year,
          posterUrl: r.Movie.posterUrl,
          userRating: r.score,
          tmdbRating: r.Movie.tmdbRating,
          actors: r.Movie.actors,
          director: r.Movie.director
        }));
        setRatedMovies(processedRatings);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchFriends = async () => {
    try {
      const res = await api.get('/friends');
      setFriends(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchRequests = async () => {
    try {
      const res = await api.get('/friends/requests');
      setRequests(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.put('/users/me', {
        firstName: editFirstName,
        lastName: editLastName,
        profilePicture: editProfilePicture,
        imdbProfileUrl: editImdbProfileUrl
      });
      setIsEditing(false);
      fetchProfile();
    } catch (err) {
      console.error(err);
      alert('Failed to update profile');
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.get(`/users/search?q=${searchQuery}`);
      setSearchResults(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const sendRequest = async (userId: number) => {
    try {
      await api.post('/friends/request', { addresseeId: userId });
      alert('Request sent!');
    } catch (err: any) {
      alert(err.response?.data?.error || 'Error sending request');
    }
  };

  const acceptRequest = async (requestId: number) => {
    try {
      await api.post(`/friends/accept/${requestId}`);
      alert('Friend request accepted!');
      fetchRequests();
      fetchFriends();
    } catch (err: any) {
      alert(err.response?.data?.error || 'Error accepting request');
    }
  };

  const removeFriend = async (friendId: number) => {
    if (!confirm('Are you sure you want to remove this friend?')) return;
    try {
      await api.delete(`/friends/${friendId}`);
      fetchFriends();
    } catch (err: any) {
      console.error('Error removing friend:', err);
      const errorMsg = err.response?.data?.error || err.message || 'Error removing friend';
      alert(errorMsg);
    }
  };

  const filterMovies = (movies: Movie[], query: string) => {
    if (!query) return movies;
    const lowerQuery = query.toLowerCase();
    return movies.filter(movie => 
      movie.title?.toLowerCase().includes(lowerQuery) ||
      movie.actors?.toLowerCase().includes(lowerQuery) ||
      movie.director?.toLowerCase().includes(lowerQuery)
    );
  };

  const MovieCard = ({ movie }: { movie: Movie }) => {
    const [imgError, setImgError] = useState(false);
    
    // Check if in lists
    const isFavorite = user?.Favorites?.some(m => m.id === movie.id) || false;
    const isWishlisted = user?.Watchlist?.some(m => m.id === movie.id) || false;
    
    // Check if rated (if not passed in movie object)
    let displayRating = movie.userRating;
    if (!displayRating) {
        const foundRating = ratedMovies.find(m => m.id === movie.id);
        if (foundRating) displayRating = foundRating.userRating;
    }

    const toggleFavorite = async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!user) return;
      
      try {
        if (isFavorite) {
          await api.delete(`/users/me/favorites/${movie.id}`);
          // Update local state
          setUser(prev => prev ? ({
            ...prev,
            Favorites: prev.Favorites?.filter(m => m.id !== movie.id) || []
          }) : null);
        } else {
          // Cast to Movie for state update
          const movieToAdd = {
             id: movie.id,
             title: movie.title,
             posterUrl: movie.posterUrl || '',
             year: movie.year
          };
          await api.post('/users/me/favorites', { movieId: movie.id });
          // Update local state
          setUser(prev => prev ? ({
            ...prev,
            Favorites: [...(prev.Favorites || []), movieToAdd]
          }) : null);
        }
      } catch (err) {
        console.error('Error toggling favorite:', err);
      }
    };

    const toggleWishlist = async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!user) return;

      try {
        if (isWishlisted) {
          await api.delete(`/users/me/watchlist/${movie.id}`);
           setUser(prev => prev ? ({
            ...prev,
            Watchlist: prev.Watchlist?.filter(m => m.id !== movie.id) || []
          }) : null);
        } else {
          const movieToAdd = {
             id: movie.id,
             title: movie.title,
             posterUrl: movie.posterUrl || '',
             year: movie.year
          };
          await api.post('/users/me/watchlist', { movieId: movie.id });
           setUser(prev => prev ? ({
            ...prev,
            Watchlist: [...(prev.Watchlist || []), movieToAdd]
          }) : null);
        }
      } catch (err) {
        console.error('Error toggling watchlist:', err);
      }
    };

    return (
      <Link 
        to={`/movie/${movie.id}`} 
        className="group block bg-gray-800 rounded-xl overflow-hidden shadow-lg border border-gray-700 hover:shadow-2xl hover:border-gray-600 transition-all duration-300 transform hover:-translate-y-1"
      >
        <div className="relative aspect-[2/3] bg-gray-700 overflow-hidden">
          {movie.posterUrl && !imgError ? (
            <img 
              src={movie.posterUrl} 
              alt={movie.title} 
              onError={() => setImgError(true)}
              className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-500" 
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 bg-gray-800">
              <span className="text-4xl">🎬</span>
            </div>
          )}
          
          {/* Rating Badges */}
          <div className="absolute top-2 left-2 z-20 flex flex-col gap-1">
            {displayRating && (
                <div className="bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded shadow border border-blue-400 flex items-center gap-1">
                  <span>★</span> {displayRating}
                </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="absolute top-2 right-2 flex flex-col gap-2 z-20 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <button 
              onClick={toggleFavorite}
              className="p-2 bg-black/60 hover:bg-red-600/80 rounded-full backdrop-blur-sm transition-all duration-200 group/btn"
              title="Add to Favorites"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className={`h-5 w-5 ${isFavorite ? 'text-red-500 fill-current' : 'text-white group-hover/btn:text-white'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </button>
            <button 
              onClick={toggleWishlist}
              className="p-2 bg-black/60 hover:bg-yellow-600/80 rounded-full backdrop-blur-sm transition-all duration-200 group/btn"
              title="Add to Wishlist"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className={`h-5 w-5 ${isWishlisted ? 'text-yellow-400 fill-current' : 'text-white group-hover/btn:text-white'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
            </button>
          </div>

          <div className="absolute inset-0 bg-gradient-to-t from-black/90 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-4">
            <span className="text-blue-400 font-medium text-sm">View Details</span>
          </div>
        </div>
        <div className="p-4">
          <h3 className="font-bold text-gray-100 truncate text-lg mb-1" title={movie.title}>{movie.title}</h3>
          <div className="flex justify-between items-center">
            <p className="text-sm text-gray-400 font-medium">{movie.year || 'N/A'}</p>
            {movie.tmdbRating && (
              <span className="text-xs font-bold text-green-400 flex items-center gap-1 bg-green-900/30 px-2 py-0.5 rounded border border-green-500/30">
                TMDB {movie.tmdbRating}
              </span>
            )}
          </div>
        </div>
      </Link>
    );
  };

  if (!user) return <div className="text-white text-center mt-10">Loading profile...</div>;

  return (
    <div className="container mx-auto p-6">
      {/* Profile Header */}
      <div className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 p-8 mb-8 flex flex-col xl:flex-row gap-8">
        
        {/* Left Side: User Info */}
        <div className="flex flex-col md:flex-row items-center md:items-start gap-8 flex-1">
            <div className="flex-shrink-0">
            {user.profilePicture ? (
                <img 
                src={user.profilePicture} 
                alt={user.username} 
                className="w-32 h-32 md:w-40 md:h-40 rounded-full object-cover border-4 border-blue-500 shadow-lg"
                />
            ) : (
                <div className="w-32 h-32 md:w-40 md:h-40 rounded-full bg-gray-700 flex items-center justify-center border-4 border-gray-600">
                <span className="text-5xl text-gray-400 uppercase">{user.username.charAt(0)}</span>
                </div>
            )}
            </div>
            
            <div className="flex-1 text-center md:text-left">
            {isEditing ? (
                <form onSubmit={handleUpdateProfile} className="space-y-4 max-w-md">
                <div className="grid grid-cols-2 gap-4">
                    <input
                    type="text"
                    placeholder="First Name"
                    value={editFirstName}
                    onChange={(e) => setEditFirstName(e.target.value)}
                    className="bg-gray-700 border border-gray-600 text-white p-2 rounded"
                    />
                    <input
                    type="text"
                    placeholder="Last Name"
                    value={editLastName}
                    onChange={(e) => setEditLastName(e.target.value)}
                    className="bg-gray-700 border border-gray-600 text-white p-2 rounded"
                    />
                </div>
                <input
                    type="text"
                    placeholder="Profile Picture URL"
                    value={editProfilePicture}
                    onChange={(e) => setEditProfilePicture(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 text-white p-2 rounded"
                />
                <input
                    type="text"
                    placeholder="IMDb Profile URL"
                    value={editImdbProfileUrl}
                    onChange={(e) => setEditImdbProfileUrl(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 text-white p-2 rounded"
                />
                <div className="flex gap-2">
                    <button type="submit" className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">Save</button>
                    <button type="button" onClick={() => setIsEditing(false)} className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded">Cancel</button>
                </div>
                </form>
            ) : (
                <>
                <h1 className="text-4xl md:text-5xl font-bold text-white mb-2">{user.username}</h1>
                {(user.firstName || user.lastName) && (
                    <h2 className="text-xl text-gray-300 mb-4 font-medium">
                    {user.firstName} {user.lastName}
                    </h2>
                )}
                {user.imdbProfileUrl && (
                    <div className="flex gap-3 mb-4">
                    <a 
                        href={user.imdbProfileUrl} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="inline-block bg-yellow-500 text-black font-bold px-3 py-1 rounded hover:bg-yellow-400 transition"
                    >
                        IMDb Profile
                    </a>
                    </div>
                )}
                <div className="mt-2">
                    <button 
                    onClick={() => setIsEditing(true)}
                    className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition shadow"
                    >
                    Edit Profile
                    </button>
                </div>
                </>
            )}
            </div>
        </div>

        {/* Right Side: Friends Panel */}
        <div className="w-full xl:w-96 border-t xl:border-t-0 xl:border-l border-gray-700 pt-6 xl:pt-0 xl:pl-6 flex flex-col gap-6">
            
            {/* Friend Requests */}
            {requests.length > 0 && (
              <div>
                <h3 className="text-lg font-bold text-green-400 mb-3">Friend Requests ({requests.length})</h3>
                <div className="max-h-40 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
                    {requests.map(req => (
                    <li key={req.id} className="p-2 border border-gray-600 rounded bg-gray-700/50 text-gray-200 flex items-center justify-between text-sm">
                        <div className="flex items-center overflow-hidden">
                          <div className="w-6 h-6 rounded-full bg-gray-600 mr-2 overflow-hidden flex-shrink-0">
                          {req.Requester.profilePicture ? <img src={req.Requester.profilePicture} className="w-full h-full object-cover" /> : null}
                          </div>
                          <span className="truncate max-w-[100px]">{req.Requester.username}</span>
                        </div>
                        <button 
                          onClick={() => acceptRequest(req.id)}
                          className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded transition flex-shrink-0"
                        >
                          Accept
                        </button>
                    </li>
                    ))}
                </div>
              </div>
            )}

            {/* My Friends */}
            <div>
                <h3 className="text-lg font-bold text-blue-400 mb-3">My Friends ({friends.length})</h3>
                <div className="max-h-40 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
                    {friends.map(friend => (
                    <li key={friend.id} className="p-2 border border-gray-600 rounded bg-gray-700/50 text-gray-200 flex items-center justify-between text-sm hover:bg-gray-700 transition group">
                        <Link to={`/profile/${friend.username}`} className="flex items-center overflow-hidden">
                          <div className="w-6 h-6 rounded-full bg-gray-600 mr-2 overflow-hidden flex-shrink-0">
                          {friend.profilePicture ? <img src={friend.profilePicture} className="w-full h-full object-cover" /> : null}
                          </div>
                          <span className="truncate">{friend.username}</span>
                        </Link>
                        <button
                            onClick={(e) => {
                                e.preventDefault();
                                removeFriend(friend.id);
                            }}
                            className="text-xs bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition"
                        >
                            Remove
                        </button>
                    </li>
                    ))}
                    {friends.length === 0 && <p className="text-gray-500 text-sm italic">No friends yet.</p>}
                </div>
            </div>

            {/* Add Friends */}
            <div>
                <h3 className="text-lg font-bold text-purple-400 mb-3">Add Friends</h3>
                <form onSubmit={handleSearch} className="flex gap-2 mb-3">
                    <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Username..."
                    className="flex-1 border border-gray-600 bg-gray-700 text-white px-3 py-1.5 rounded text-sm focus:outline-none focus:border-purple-500"
                    />
                    <button type="submit" className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1.5 rounded text-sm transition">Search</button>
                </form>
                {searchResults.length > 0 && (
                    <ul className="max-h-40 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
                    {searchResults.map(user => (
                        <li key={user.id} className="flex justify-between items-center p-2 border border-gray-600 rounded bg-gray-700/50 text-sm">
                        <Link to={`/profile/${user.username}`} className="flex items-center overflow-hidden mr-2 hover:text-blue-400">
                           <span className="text-gray-200 truncate">{user.username}</span>
                        </Link>
                        <button 
                            onClick={() => sendRequest(user.id)}
                            className="text-xs bg-green-600 hover:bg-green-700 text-white px-2 py-1 rounded transition flex-shrink-0"
                        >
                            Add
                        </button>
                        </li>
                    ))}
                    </ul>
                )}
                {searchResults.length === 0 && searchQuery && <p className="text-gray-500 text-sm">No users found.</p>}
            </div>
        </div>

      </div>

      {/* Lists Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        
        {/* Rated Movies */}
        {ratedMovies.length > 0 && (
          <div className="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700 lg:col-span-2">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
              <h2 className="text-2xl font-bold text-blue-400 flex items-center gap-2">
                <span>⭐</span> Rated Movies ({ratedMovies.length})
              </h2>
              <input
                type="text"
                placeholder="Search rated movies..."
                value={searchRated}
                onChange={(e) => setSearchRated(e.target.value)}
                className="bg-gray-700 border border-gray-600 text-white px-3 py-1.5 rounded text-sm focus:outline-none focus:border-blue-500 w-full sm:w-64"
              />
            </div>
            <div className="flex overflow-x-auto gap-4 pb-4 custom-scrollbar">
              {filterMovies(ratedMovies, searchRated).map((movie, idx) => (
                <div key={idx} className="min-w-[160px] w-[160px] sm:min-w-[180px] sm:w-[180px] flex-shrink-0">
                  <MovieCard movie={movie} />
                </div>
              ))}
              {filterMovies(ratedMovies, searchRated).length === 0 && (
                <p className="text-gray-500 italic p-4">No movies found matching "{searchRated}"</p>
              )}
            </div>
          </div>
        )}

        {/* Watchlist */}
        <div className="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
            <h2 className="text-2xl font-bold text-yellow-400 flex items-center gap-2">
              <span>📺</span> Watchlist {user.Watchlist && user.Watchlist.length > 0 && `(${user.Watchlist.length})`}
            </h2>
            <input
              type="text"
              placeholder="Search watchlist..."
              value={searchWatchlist}
              onChange={(e) => setSearchWatchlist(e.target.value)}
              className="bg-gray-700 border border-gray-600 text-white px-3 py-1.5 rounded text-sm focus:outline-none focus:border-yellow-500 w-full sm:w-48"
            />
          </div>
          {user.Watchlist && user.Watchlist.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 max-h-[800px] overflow-y-auto pr-2 custom-scrollbar">
              {filterMovies(user.Watchlist, searchWatchlist).map(movie => (
                <MovieCard key={movie.id} movie={movie} />
              ))}
              {filterMovies(user.Watchlist, searchWatchlist).length === 0 && (
                <p className="text-gray-500 italic col-span-full text-center py-4">No movies found.</p>
              )}
            </div>
          ) : (
            <p className="text-gray-500 italic">Your watchlist is empty.</p>
          )}
        </div>

        {/* Favorites */}
        <div className="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
            <h2 className="text-2xl font-bold text-red-400 flex items-center gap-2">
              <span>❤️</span> Favorites {user.Favorites && user.Favorites.length > 0 && `(${user.Favorites.length})`}
            </h2>
            <input
              type="text"
              placeholder="Search favorites..."
              value={searchFavorites}
              onChange={(e) => setSearchFavorites(e.target.value)}
              className="bg-gray-700 border border-gray-600 text-white px-3 py-1.5 rounded text-sm focus:outline-none focus:border-red-500 w-full sm:w-48"
            />
          </div>
          {user.Favorites && user.Favorites.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 max-h-[800px] overflow-y-auto pr-2 custom-scrollbar">
              {filterMovies(user.Favorites, searchFavorites).map(movie => (
                <MovieCard key={movie.id} movie={movie} />
              ))}
              {filterMovies(user.Favorites, searchFavorites).length === 0 && (
                <p className="text-gray-500 italic col-span-full text-center py-4">No movies found.</p>
              )}
            </div>
          ) : (
            <p className="text-gray-500 italic">No favorites yet.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Profile;
