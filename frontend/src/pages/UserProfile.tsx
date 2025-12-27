import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../api/axios';

interface Movie {
  id: number;
  title: string;
  posterUrl: string;
  year?: number;
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
  Ratings?: any[];
  isFriend?: boolean;
}

const UserProfile = () => {
  const { username } = useParams<{ username: string }>();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Search States
  const [searchRated, setSearchRated] = useState('');
  const [searchWatchlist, setSearchWatchlist] = useState('');
  const [searchFavorites, setSearchFavorites] = useState('');

  useEffect(() => {
    fetchUserProfile();
  }, [username]);

  const fetchUserProfile = async () => {
    try {
      const res = await api.get(`/users/${username}`);
      setUser(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const sendRequest = async () => {
    if (!user) return;
    try {
      await api.post('/friends/request', { addresseeId: user.id });
      alert('Friend request sent!');
    } catch (err: any) {
      alert(err.response?.data?.error || 'Error sending request');
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

  const filterRatings = (ratings: any[], query: string) => {
    if (!query) return ratings;
    const lowerQuery = query.toLowerCase();
    return ratings.filter(rating => 
      rating.Movie.title?.toLowerCase().includes(lowerQuery) ||
      rating.Movie.actors?.toLowerCase().includes(lowerQuery) ||
      rating.Movie.director?.toLowerCase().includes(lowerQuery)
    );
  };

  const MovieCard = ({ movie }: { movie: Movie }) => {
    const [imgError, setImgError] = useState(false);
    
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
          
          {/* TMDB Rating Badge */}
          
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

  if (loading) return <div className="text-white text-center mt-10">Loading profile...</div>;
  if (!user) return <div className="text-white text-center mt-10">User not found.</div>;

  return (
    <div className="container mx-auto p-6">
      {/* Profile Header */}
      <div className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 p-8 mb-8 flex flex-col md:flex-row items-center md:items-start gap-8">
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
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-2">{user.username}</h1>
          {(user.firstName || user.lastName) && (
            <h2 className="text-xl text-gray-300 mb-4 font-medium">
              {user.firstName} {user.lastName}
            </h2>
          )}
          
          {!user.isFriend && (
            <button 
              onClick={sendRequest}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition shadow-lg mb-4"
            >
              Add Friend
            </button>
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
        </div>
      </div>

      {/* Lists Section */}
      {user.isFriend ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Rated Movies */}
          {user.Ratings && user.Ratings.length > 0 && (
            <div className="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700 lg:col-span-2">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
                <h2 className="text-2xl font-bold text-blue-400 flex items-center gap-2">
                  <span>⭐</span> Rated Movies ({user.Ratings.length})
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
                {filterRatings(user.Ratings, searchRated).map((rating, idx) => (
                  <div key={idx} className="min-w-[160px] w-[160px] sm:min-w-[180px] sm:w-[180px] flex-shrink-0">
                    <div className="bg-gray-700 rounded overflow-hidden group h-full border border-gray-600 shadow-lg">
                    <Link to={`/movie/${rating.Movie.id}`} className="block h-full">
                      <div className="aspect-[2/3] bg-gray-600 relative">
                        {rating.Movie.posterUrl ? (
                          <img src={rating.Movie.posterUrl} alt={rating.Movie.title} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-gray-500 text-xs">No Img</div>
                        )}
                        <div className="absolute top-1 right-1 flex flex-col gap-1 items-end">
                          <div className="bg-blue-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow border border-blue-400" title="User Rating">
                            ★ {rating.score}
                          </div>
                        </div>
                      </div>
                      <div className="p-2">
                        <p className="text-xs text-white font-medium truncate text-center" title={rating.Movie.title}>{rating.Movie.title}</p>
                        <div className="flex justify-center items-center gap-2 mt-1">
                          <p className="text-[10px] text-gray-400">{rating.Movie.year}</p>
                          {rating.Movie.tmdbRating && (
                            <span className="text-[10px] font-bold text-green-400 flex items-center gap-0.5 bg-green-900/30 px-1 py-0.5 rounded border border-green-500/30">
                              TMDB {rating.Movie.tmdbRating}
                            </span>
                          )}
                        </div>
                      </div>
                    </Link>
                    </div>
                  </div>
                ))}
                {filterRatings(user.Ratings, searchRated).length === 0 && (
                  <p className="text-gray-500 italic p-4">No movies found matching "{searchRated}"</p>
                )}
              </div>
            </div>
          )}

          {/* Watchlist */}
          <div className="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
              <h2 className="text-2xl font-bold text-yellow-400 flex items-center gap-2">
                <span>📺</span> Watchlist
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
              <p className="text-gray-500 italic">Watchlist is empty.</p>
            )}
          </div>

          {/* Favorites */}
          <div className="bg-gray-800 p-6 rounded-xl shadow-lg border border-gray-700">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
              <h2 className="text-2xl font-bold text-red-400 flex items-center gap-2">
                <span>❤️</span> Favorites
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
      ) : (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-12 text-center">
          <div className="text-6xl mb-4">🔒</div>
          <h2 className="text-2xl font-bold text-white mb-2">Private Profile</h2>
          <p className="text-gray-400">Add {user.username} as a friend to see their Watchlist and Favorites.</p>
        </div>
      )}
    </div>
  );
};

export default UserProfile;
