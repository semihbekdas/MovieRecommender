const axios = require('axios');
const { Movie } = require('../models');
require('dotenv').config();

const TMDB_API_KEY = process.env.TMDB_API_KEY;
const TMDB_BASE_URL = 'https://api.themoviedb.org/3';

/**
 * Fetches the current rating from TMDB.
 * Does NOT save the rating to the database, but will save the tmdbId if found.
 * @param {Object} movie - Sequelize Movie instance
 * @returns {Promise<string|null>} - The rating formatted as string (e.g. "7.5") or null
 */
async function getTmdbRating(movie) {
  if (!TMDB_API_KEY) {
    console.log('TMDB_API_KEY is missing');
    return null;
  }

  try {
    let tmdbId = movie.tmdbId;
    let rating = null;

    if (tmdbId) {
      // Fetch details directly using ID
      try {
        const res = await axios.get(`${TMDB_BASE_URL}/movie/${tmdbId}`, {
          params: { api_key: TMDB_API_KEY },
          proxy: false
        });
        rating = res.data.vote_average;
      } catch (err) {
        if (err.response && err.response.status === 404) {
           // TMDB ID not found, will try search fallback
        }
      }
    } 
    
    // If no rating found yet (either no ID, or ID lookup failed)
    if (!rating) {
      // Search for the movie
      const cleanTitle = movie.title.replace(/\s*\(\d{4}\)\s*$/, '').trim();
      
      const res = await axios.get(`${TMDB_BASE_URL}/search/movie`, {
        params: {
          api_key: TMDB_API_KEY,
          query: cleanTitle,
          year: movie.year,
          include_adult: false
        },
        proxy: false
      });

      if (res.data.results && res.data.results.length > 0) {
        const bestMatch = res.data.results[0];
        tmdbId = bestMatch.id;
        rating = bestMatch.vote_average;
        
        // Save/Update the TMDB ID
        if (movie.tmdbId !== tmdbId) {
          movie.tmdbId = tmdbId;
          await movie.save();
        }
      }
    }

    return rating !== null && rating !== undefined ? rating.toFixed(1) : null;
  } catch (error) {
    console.error(`Error fetching TMDB rating for ${movie.title}:`, error.message);
    return null;
  }
}

module.exports = { getTmdbRating };
