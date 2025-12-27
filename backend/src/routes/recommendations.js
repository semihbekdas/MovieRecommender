const express = require('express');
const router = express.Router();
const axios = require('axios');
const { Op } = require('sequelize');
const authMiddleware = require('../middleware/authMiddleware');
const { MODEL_1_URL, MODEL_2_URL, MODEL_3_URL } = require('../config/recommenderServices');
const { Movie, User } = require('../models');
const { ensureMoviePoster } = require('../services/posterService');
const { getTmdbRating } = require('../services/tmdbService');

// Helper to fetch movie details for recommended IDs
async function hydrateMovies(movieIds) {
  return await Movie.findAll({
    where: {
      id: movieIds
    }
  });
}

// Get recommendations from Model 1 (Association Rules)
router.get('/model1', authMiddleware, async (req, res) => {
  try {
    // 1. Get user's favorite movies
    const user = await User.findByPk(req.user.id, {
      include: [{ model: Movie, as: 'Favorites' }]
    });

    if (!user || !user.Favorites || user.Favorites.length === 0) {
      return res.json([]); // No favorites, no recommendations
    }

    const likedTitles = user.Favorites.map(m => m.title);

    // 2. Call Python API
    const response = await axios.post(MODEL_1_URL, { 
      liked_movies: likedTitles,
      top_n: 10
    });

    if (!response.data.success) {
      console.error('[Model 1] Python API returned error:', response.data.error);
      throw new Error(response.data.error || 'Unknown error from model service');
    }

    const recommendations = response.data.recommendations;

    if (recommendations.length === 0) {
      return res.json([]);
    }

    // 3. Get recommended titles
    const recommendedTitles = recommendations.map(r => r.title);

    // 4. Fetch full movie objects from our DB
    const movies = await Movie.findAll({
      where: {
        title: {
          [Op.in]: recommendedTitles
        }
      }
    });

    // Log missing movies for debugging
    const foundTitles = movies.map(m => m.title);
    const missingTitles = recommendedTitles.filter(t => !foundTitles.includes(t));
    if (missingTitles.length > 0) {
      console.log('[Model 1] Movies not found in DB:', missingTitles);
    }

    // 5. Create a map of title -> score for ordering
    const scoreMap = new Map();
    recommendations.forEach(r => {
      scoreMap.set(r.title, r.score || 0);
    });
    
    // 6. Ensure posters are available and fetch ratings
    const moviesWithRatings = await Promise.all(movies.map(async (movie) => {
      await ensureMoviePoster(movie);
      const tmdbRating = await getTmdbRating(movie);
      const movieData = movie.toJSON();
      movieData.tmdbRating = tmdbRating;
      movieData.score = scoreMap.get(movie.title) || 0;
      return movieData;
    }));

    // 7. Sort by score (descending) to preserve original order
    moviesWithRatings.sort((a, b) => b.score - a.score);

    res.json(moviesWithRatings);
  } catch (error) {
    console.error('Model 1 Error:', error.message);
    if (error.response) {
        console.error('Python API Response Data:', error.response.data);
    }
    res.json([]);
  }
});

// Get recommendations from Model 2 (Content-Based)
router.get('/model2', authMiddleware, async (req, res) => {
  try {
    // 1. Get user's favorite movies
    const user = await User.findByPk(req.user.id, {
      include: [{ model: Movie, as: 'Favorites' }]
    });

    if (!user || !user.Favorites || user.Favorites.length === 0) {
      return res.json([]); 
    }

    const likedTitles = user.Favorites.map(m => m.title);

    // 2. Call Python API
    const response = await axios.post(MODEL_2_URL, { 
      liked_movies: likedTitles,
      top_n: 10
    });

    if (!response.data.success) {
      console.error('[Model 2] Python API returned error:', response.data.error);
      throw new Error(response.data.error || 'Unknown error from model service');
    }

    const recommendations = response.data.recommendations;

    if (recommendations.length === 0) {
      return res.json([]);
    }

    // 3. Get recommended titles with their similarity scores
    const recommendedTitles = recommendations.map(r => r.title);

    // 4. Fetch full movie objects from our DB
    const movies = await Movie.findAll({
      where: {
        title: {
          [Op.in]: recommendedTitles
        }
      }
    });

    // Log missing movies for debugging
    const foundTitles = movies.map(m => m.title);
    const missingTitles = recommendedTitles.filter(t => !foundTitles.includes(t));
    if (missingTitles.length > 0) {
      console.log('[Model 2] Movies not found in DB:', missingTitles);
    }
    
    // 5. Create a map of title -> similarity for ordering
    const similarityMap = new Map();
    recommendations.forEach(r => {
      similarityMap.set(r.title, r.similarity || 0);
    });

    // 6. Ensure posters are available and fetch ratings
    const moviesWithRatings = await Promise.all(movies.map(async (movie) => {
      await ensureMoviePoster(movie);
      const tmdbRating = await getTmdbRating(movie);
      const movieData = movie.toJSON();
      movieData.tmdbRating = tmdbRating;
      movieData.similarity = similarityMap.get(movie.title) || 0;
      return movieData;
    }));

    // 7. Sort by similarity (descending) to preserve original order
    moviesWithRatings.sort((a, b) => b.similarity - a.similarity);

    res.json(moviesWithRatings);

  } catch (error) {
    console.error('Model 2 Error:', error.message);
    if (error.response) {
        console.error('Python API Response Data:', error.response.data);
    }
    res.json([]);
  }
});

// Get recommendations from Model 3 (Item-Based CF)
router.get('/model3', authMiddleware, async (req, res) => {
  try {
    // 1. Get user's favorite movies
    const user = await User.findByPk(req.user.id, {
      include: [{ model: Movie, as: 'Favorites' }]
    });

    if (!user || !user.Favorites || user.Favorites.length === 0) {
      return res.json([]); 
    }

    const likedTitles = user.Favorites.map(m => m.title);

    // 2. Call Python API
    const response = await axios.post(MODEL_3_URL, { 
      liked_movies: likedTitles,
      top_n: 10
    });

    if (!response.data.success) {
      console.error('[Model 3] Python API returned error:', response.data.error);
      throw new Error(response.data.error || 'Unknown error from model service');
    }

    const recommendations = response.data.recommendations;

    if (recommendations.length === 0) {
      return res.json([]);
    }

    // 3. Get recommended titles
    const recommendedTitles = recommendations.map(r => r.title);

    // 4. Fetch full movie objects from our DB
    const movies = await Movie.findAll({
      where: {
        title: {
          [Op.in]: recommendedTitles
        }
      }
    });

    // Log missing movies for debugging
    const foundTitles = movies.map(m => m.title);
    const missingTitles = recommendedTitles.filter(t => !foundTitles.includes(t));
    if (missingTitles.length > 0) {
      console.log('[Model 3] Movies not found in DB:', missingTitles);
    }

    // 5. Create a map of title -> similarity for ordering
    const similarityMap = new Map();
    recommendations.forEach(r => {
      similarityMap.set(r.title, r.similarity || r.score || 0);
    });
    
    // 6. Ensure posters are available and fetch ratings
    const moviesWithRatings = await Promise.all(movies.map(async (movie) => {
      await ensureMoviePoster(movie);
      const tmdbRating = await getTmdbRating(movie);
      const movieData = movie.toJSON();
      movieData.tmdbRating = tmdbRating;
      movieData.similarity = similarityMap.get(movie.title) || 0;
      return movieData;
    }));

    // 7. Sort by similarity (descending) to preserve original order
    moviesWithRatings.sort((a, b) => b.similarity - a.similarity);

    res.json(moviesWithRatings);

  } catch (error) {
    console.error('Model 3 Error:', error.message);
    if (error.response) {
        console.error('Python API Response Data:', error.response.data);
    }
    res.json([]);
  }
});

module.exports = router;
