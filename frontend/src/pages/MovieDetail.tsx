import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api/axios';

interface MovieDetail {
  id: number;
  title: string;
  year: number;
  description: string;
  genres: string;
  actors: string;
  director: string;
  posterUrl: string;
  tmdbRating?: string;
}

const MovieDetail = () => {
  const { id } = useParams<{ id: string }>();
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [rating, setRating] = useState(0);
  const [message, setMessage] = useState('');
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    const fetchMovie = async () => {
      try {
        const res = await api.get(`/movies/${id}`);
        setMovie(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    
    const checkLists = async () => {
      try {
        const res = await api.get('/users/me');
        const watchlist = res.data.Watchlist || [];
        const favorites = res.data.Favorites || [];
        const ratings = res.data.Ratings || [];
        
        if (id) {
          const movieId = parseInt(id);
          setIsInWatchlist(watchlist.some((m: any) => m.id === movieId));
          setIsFavorite(favorites.some((m: any) => m.id === movieId));

          const userRating = ratings.find((r: any) => r.movieId === movieId || (r.Movie && r.Movie.id === movieId));
          if (userRating) {
            setRating(userRating.score);
          }
        }
      } catch (err) {
        console.error(err);
      }
    };

    fetchMovie();
    checkLists();
  }, [id]);

  const handleRate = async (score: number) => {
    try {
      await api.post(`/movies/${id}/rate`, { score });
      setRating(score);
      setMessage('Rating saved!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      console.error(err);
      setMessage('Error saving rating');
    }
  };

  const toggleWatchlist = async () => {
    try {
      if (isInWatchlist) {
        await api.delete(`/users/me/watchlist/${id}`);
        setIsInWatchlist(false);
        setMessage('Removed from Watchlist');
      } else {
        await api.post('/users/me/watchlist', { movieId: id });
        setIsInWatchlist(true);
        setMessage('Added to Watchlist');
      }
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      console.error(err);
    }
  };

  const toggleFavorite = async () => {
    try {
      if (isFavorite) {
        await api.delete(`/users/me/favorites/${id}`);
        setIsFavorite(false);
        setMessage('Removed from Favorites');
      } else {
        await api.post('/users/me/favorites', { movieId: id });
        setIsFavorite(true);
        setMessage('Added to Favorites');
      }
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      console.error(err);
    }
  };

  if (!movie) return (
    <div className="flex justify-center items-center min-h-[50vh]">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
    </div>
  );

  return (
    <div className="container mx-auto px-6 py-10">
      <Link to="/" className="inline-flex items-center text-gray-400 hover:text-blue-400 mb-6 transition">
        ← Back to Movies
      </Link>
      
      <div className="bg-gray-800 rounded-2xl shadow-xl overflow-hidden border border-gray-700">
        <div className="flex flex-col md:flex-row">
          {/* Poster Section */}
          <div className="w-full md:w-1/3 lg:w-1/4 bg-gray-900">
            <div className="aspect-[2/3] relative">
               {movie.posterUrl && !imgError ? (
                 <img 
                   src={movie.posterUrl} 
                   alt={movie.title} 
                   onError={() => setImgError(true)}
                   className="absolute inset-0 w-full h-full object-cover" 
                 />
               ) : (
                 <div className="flex items-center justify-center h-full text-gray-600">
                   <span className="text-6xl">🎬</span>
                 </div>
               )}
            </div>
          </div>

          {/* Details Section */}
          <div className="w-full md:w-2/3 lg:w-3/4 p-8 md:p-10 flex flex-col justify-between">
            <div>
              <div className="flex flex-wrap items-baseline gap-4 mb-2">
                <h1 className="text-4xl font-bold text-white">{movie.title}</h1>
                <span className="text-2xl text-gray-400 font-light">({movie.year})</span>
                {movie.tmdbRating && (
                  <span className="px-3 py-1 bg-green-500/20 text-green-400 border border-green-500/50 rounded-lg text-lg font-bold flex items-center gap-1">
                    <span className="text-xl">★</span> {movie.tmdbRating}
                  </span>
                )}
              </div>
              
              <div className="flex flex-wrap gap-2 mb-6">
                {movie.genres?.split(',').map((genre, idx) => (
                  <span key={idx} className="px-3 py-1 bg-blue-900/30 text-blue-400 rounded-full text-sm font-medium border border-blue-800">
                    {genre.trim()}
                  </span>
                ))}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 mb-8">
                <button 
                  onClick={toggleWatchlist}
                  className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
                    isInWatchlist 
                      ? 'bg-yellow-600/20 text-yellow-400 border border-yellow-600/50 hover:bg-yellow-600/30' 
                      : 'bg-gray-700 text-gray-300 border border-gray-600 hover:bg-gray-600'
                  }`}
                >
                  {isInWatchlist ? '✓ In Watchlist' : '+ Add to Watchlist'}
                </button>
                <button 
                  onClick={toggleFavorite}
                  className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
                    isFavorite 
                      ? 'bg-red-600/20 text-red-400 border border-red-600/50 hover:bg-red-600/30' 
                      : 'bg-gray-700 text-gray-300 border border-gray-600 hover:bg-gray-600'
                  }`}
                >
                  {isFavorite ? '❤️ Favorited' : '♡ Add to Favorites'}
                </button>
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-1">Overview</h3>
                  <p className="text-gray-300 leading-relaxed text-lg">{movie.description}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-1">Director</h3>
                    <p className="text-white font-medium">{movie.director}</p>
                  </div>
                  <div>
                    <h3 className="text-sm uppercase tracking-wide text-gray-500 font-semibold mb-1">Cast</h3>
                    <p className="text-white font-medium">{movie.actors}</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Rating Section */}
            <div className="mt-10 pt-8 border-t border-gray-700">
              <h3 className="text-lg font-bold text-white mb-3">Rate this movie</h3>
              <div className="flex items-center gap-4">
                <div className="flex space-x-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => handleRate(star)}
                      onMouseEnter={() => setRating(star)}
                      className={`text-4xl transition-transform hover:scale-110 focus:outline-none ${
                        star <= rating ? 'text-yellow-400' : 'text-gray-600 hover:text-yellow-200'
                      }`}
                    >
                      ★
                    </button>
                  ))}
                </div>
                {message && (
                  <span className={`px-4 py-2 rounded-lg text-sm font-medium animate-fade-in ${
                    message.includes('Error') ? 'bg-red-900/20 text-red-400' : 'bg-green-900/20 text-green-400'
                  }`}>
                    {message}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MovieDetail;
