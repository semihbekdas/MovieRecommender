const axios = require('axios');
const cheerio = require('cheerio');
const { Movie } = require('../models');
const { Op } = require('sequelize');
require('dotenv').config();

const TMDB_API_KEY = process.env.TMDB_API_KEY;
const TMDB_BASE_URL = 'https://api.themoviedb.org/3';
const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500';

// User-Agent to mimic a real browser (still used for IMDb fallback)
const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
};

/**
 * Fetches movie poster using TMDB API
 * @param {string} title 
 * @param {number} year 
 * @returns {Promise<string|null>} Poster URL
 */
async function scrapeTmdb(title, year) {
  if (!TMDB_API_KEY || TMDB_API_KEY === 'YOUR_TMDB_API_KEY_HERE') {
    console.warn('[PosterService] TMDB API Key is missing or invalid. Please check .env file.');
    return null;
  }

  // Clean title: remove year in parentheses if present, e.g. "Movie (2020)" -> "Movie"
  const cleanTitle = title.replace(/\s*\(\d{4}\)\s*$/, '').trim();

  try {
    // Strategy 1: Search with Title + Year
    let response = await axios.get(`${TMDB_BASE_URL}/search/movie`, {
      params: {
        api_key: TMDB_API_KEY,
        query: cleanTitle,
        year: year,
        include_adult: false
      },
      proxy: false
    });

    // Strategy 2: If no results, try searching WITHOUT year (in case DB year is wrong)
    if (response.data.results.length === 0 && year) {
       console.log(`[PosterService] No results for '${cleanTitle}' (${year}). Retrying without year...`);
       response = await axios.get(`${TMDB_BASE_URL}/search/movie`, {
        params: {
          api_key: TMDB_API_KEY,
          query: cleanTitle,
          include_adult: false
        },
        proxy: false
      });
    }

    const results = response.data.results;
    if (results && results.length > 0) {
      // Find the first movie that actually has a poster
      const movieWithPoster = results.find(m => m.poster_path);
      
      if (movieWithPoster) {
        return `${TMDB_IMAGE_BASE_URL}${movieWithPoster.poster_path}`;
      }
    }

    // Fallback: If TMDB fails, try scraping IMDb
    console.log(`[PosterService] TMDB failed for '${title}'. Trying IMDb fallback...`);
    return await scrapeImdb(cleanTitle);

  } catch (error) {
    console.error(`[PosterService] TMDB API request failed for ${title}:`, error.message);
    return null;
  }
}

/**
 * Scrapes IMDb for a movie poster
 * @param {string} title 
 * @returns {Promise<string|null>} Poster URL
 */
async function scrapeImdb(title) {
  try {
    const query = encodeURIComponent(title);
    const searchUrl = `https://www.imdb.com/find?q=${query}&s=tt&ttype=ft&ref_=fn_ft`;
    
    const { data } = await axios.get(searchUrl, { headers: HEADERS });
    const $ = cheerio.load(data);
    
    // Find the first result link
    const firstResult = $('.ipc-metadata-list-summary-item__t').first();
    if (!firstResult.length) return null;
    
    const href = firstResult.attr('href');
    if (!href) return null;
    
    // Go to movie page
    const movieUrl = `https://www.imdb.com${href}`;
    const moviePage = await axios.get(movieUrl, { headers: HEADERS });
    const $movie = cheerio.load(moviePage.data);
    
    // Try to find the poster image
    // IMDb structure changes often, looking for common patterns
    const posterImg = $movie('.ipc-media__img img').first();
    let src = posterImg.attr('src') || posterImg.attr('srcset');
    
    if (src) {
      // If srcset, take the last one (highest res) or just the src
      if (src.includes('w,')) {
         // Simple parsing if needed, but usually src is fine for a thumbnail
         // Let's just take the src attribute which is usually the main image
         src = posterImg.attr('src');
      }
      return src;
    }
    return null;
  } catch (error) {
    console.error(`[PosterService] IMDb Scraping failed for ${title}:`, error.message);
    return null;
  }
}

/**
 * Ensures a movie has a valid poster.
 * If missing, tries to fetch it and update the DB.
 * @param {Movie} movie - Sequelize Movie instance
 * @returns {Promise<Movie>} Updated movie instance
 */
async function ensureMoviePoster(movie) {
  // Check if poster is missing or invalid
  if (movie.posterUrl && movie.posterUrl.length > 10 && !movie.posterUrl.includes('N/A')) {
    return movie;
  }

  console.log(`[PosterService] Fetching poster for: ${movie.title}`);

  // Try TMDB first
  let newPoster = await scrapeTmdb(movie.title, movie.year);
  
  // Try IMDb if TMDB failed
  if (!newPoster) {
    newPoster = await scrapeImdb(movie.title);
  }

  if (newPoster) {
    console.log(`[PosterService] Found poster: ${newPoster}`);
    movie.posterUrl = newPoster;
    await movie.save();
  } else {
    console.log(`[PosterService] Could not find poster for: ${movie.title}`);
  }

  return movie;
}

module.exports = {
  ensureMoviePoster
};
