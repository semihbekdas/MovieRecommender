import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/axios';

interface Movie {
  id: number;
  title: string;
  year: number;
  posterUrl: string;
  tmdbRating?: string;
}

const Home = () => {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [recommendations, setRecommendations] = useState<Movie[]>([]);
  const [model, setModel] = useState('model1');
  
  // Search & Pagination State
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  
  // User Preferences State
  const [favorites, setFavorites] = useState<number[]>([]);
  const [watchlist, setWatchlist] = useState<number[]>([]);
  const [userRatings, setUserRatings] = useState<Record<number, number>>({});

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1); // Reset to page 1 on new search
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    fetchMovies();
    fetchUserData();
  }, [debouncedSearch, page]);

  useEffect(() => {
    fetchRecommendations();
  }, [model]);

  const fetchUserData = async () => {
    try {
      const res = await api.get('/users/me');
      if (res.data) {
        setFavorites(res.data.Favorites?.map((m: any) => m.id) || []);
        setWatchlist(res.data.Watchlist?.map((m: any) => m.id) || []);
        
        const ratingsMap: Record<number, number> = {};
        res.data.Ratings?.forEach((r: any) => {
            // Handle both direct movieId or nested Movie object structure depending on backend response
            const mId = r.movieId || (r.Movie && r.Movie.id);
            if (mId) ratingsMap[mId] = r.score;
        });
        setUserRatings(ratingsMap);
      }
    } catch (err) {
      console.error('Failed to fetch user data', err);
    }
  };

  const fetchMovies = async () => {
    setLoading(true);
    try {
      const res = await api.get('/movies', {
        params: {
          page,
          search: debouncedSearch
        }
      });
      setMovies(res.data.movies);
      setTotalPages(res.data.totalPages);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRecommendations = async () => {
    try {
      const res = await api.get(`/recommendations/${model}`);
      setRecommendations(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const MovieCard = ({ movie }: { movie: Movie }) => {
    const [imgError, setImgError] = useState(false);
    const isFavorite = favorites.includes(movie.id);
    const isWishlisted = watchlist.includes(movie.id);
    const userRating = userRatings[movie.id];

    const toggleFavorite = async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      try {
        if (isFavorite) {
          await api.delete(`/users/me/favorites/${movie.id}`);
          setFavorites(prev => prev.filter(id => id !== movie.id));
        } else {
          await api.post('/users/me/favorites', { movieId: movie.id });
          setFavorites(prev => [...prev, movie.id]);
        }
      } catch (err) {
        console.error('Error toggling favorite:', err);
      }
    };

    const toggleWishlist = async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      try {
        if (isWishlisted) {
          await api.delete(`/users/me/watchlist/${movie.id}`);
          setWatchlist(prev => prev.filter(id => id !== movie.id));
        } else {
          await api.post('/users/me/watchlist', { movieId: movie.id });
          setWatchlist(prev => [...prev, movie.id]);
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
          
          {/* Rating Badge */}
          {userRating && (
             <div className="absolute top-2 left-2 z-20">
                <div className="bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded shadow border border-blue-400 flex items-center gap-1">
                  <span>★</span> {userRating}
                </div>
             </div>
          )}
          
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
            <p className="text-sm text-gray-400 font-medium">{movie.year}</p>
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

  return (
    <div className="container mx-auto px-6 py-8">
      {/* Search Section */}
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-bold text-white mb-6">Find Your Next Favorite Movie</h1>
        <div className="max-w-2xl mx-auto relative">
          <input
            type="text"
            placeholder="Search movies, actors, directors..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-6 py-4 bg-gray-800 border border-gray-700 rounded-full text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-lg text-lg"
          />
          <div className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400">
            🔍
          </div>
        </div>
      </div>

      {/* Recommendations Section (Only show if not searching) */}
      {!debouncedSearch && (
        <div className="mb-12">
          <div className="flex flex-col md:flex-row justify-between items-center mb-8">
            <h2 className="text-3xl font-bold text-white border-l-4 border-blue-500 pl-4">
              Recommended for You
            </h2>
            
            <div className="flex bg-gray-800 p-1 rounded-lg mt-4 md:mt-0 border border-gray-700">
              {['model1', 'model2', 'model3'].map((m) => (
                <button 
                  key={m}
                  onClick={() => setModel(m)} 
                  className={`px-6 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                    model === m 
                      ? 'bg-gray-700 text-blue-400 shadow-sm' 
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {m.charAt(0).toUpperCase() + m.slice(1).replace('model', 'Model ')}
                </button>
              ))}
            </div>
          </div>

          {recommendations.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
              {recommendations.map(movie => (
                <MovieCard key={movie.id} movie={movie} />
              ))}
            </div>
          ) : (
            <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-8 text-center">
              <p className="text-blue-400 text-lg">No recommendations found for this model yet.</p>
            </div>
          )}
        </div>
      )}

      {/* Browse / Search Results Section */}
      <div>
        <h2 className="text-3xl font-bold text-white border-l-4 border-purple-500 pl-4 mb-8">
          {debouncedSearch ? 'Search Results' : 'Browse Movies'}
        </h2>
        
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto"></div>
          </div>
        ) : movies.length > 0 ? (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6 mb-8">
              {movies.map(movie => (
                <MovieCard key={movie.id} movie={movie} />
              ))}
            </div>
            
            {/* Pagination Controls */}
            <div className="flex justify-center items-center space-x-4">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 bg-gray-800 text-white rounded-lg disabled:opacity-50 hover:bg-gray-700 transition-colors"
              >
                Previous
              </button>
              <span className="text-gray-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 bg-gray-800 text-white rounded-lg disabled:opacity-50 hover:bg-gray-700 transition-colors"
              >
                Next
              </button>
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-gray-400">
            No movies found.
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;
