const express = require('express');
const router = express.Router();
const { Movie, Rating } = require('../models');
const { Op } = require('sequelize');
const authMiddleware = require('../middleware/authMiddleware');
const { ensureMoviePoster } = require('../services/posterService');
const { getTmdbRating } = require('../services/tmdbService');

// List movies (with pagination and search)
router.get('/', async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = 15; // Increased limit for better grid view
    const offset = (page - 1) * limit;
    const search = req.query.search || '';

    const whereClause = {};
    if (search) {
      whereClause[Op.or] = [
        { title: { [Op.like]: `%${search}%` } },
        { actors: { [Op.like]: `%${search}%` } },
        { director: { [Op.like]: `%${search}%` } }
      ];
    }

    const { count, rows } = await Movie.findAndCountAll({
      where: whereClause,
      limit,
      offset,
      order: [['year', 'DESC']] // Show newest first by default
    });

    // Ensure posters are available and fetch dynamic ratings
    const moviesWithRatings = await Promise.all(rows.map(async (movie) => {
      await ensureMoviePoster(movie);
      const tmdbRating = await getTmdbRating(movie);
      
      // Convert to plain object to attach the virtual property
      const movieData = movie.toJSON();
      movieData.tmdbRating = tmdbRating;
      return movieData;
    }));

    res.json({
      movies: moviesWithRatings,
      totalPages: Math.ceil(count / limit),
      currentPage: page,
      totalItems: count
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get movie details
router.get('/:id', async (req, res) => {
  try {
    let movie = await Movie.findByPk(req.params.id);
    if (!movie) return res.status(404).json({ error: 'Movie not found' });

    // Ensure poster exists (blocking for detail view so user sees it)
    movie = await ensureMoviePoster(movie);

    // Fetch dynamic rating
    const tmdbRating = await getTmdbRating(movie);
    const movieData = movie.toJSON();
    movieData.tmdbRating = tmdbRating;

    res.json(movieData);
  } catch (error) {
    res.status(500).json({ error: 'Server error' });
  }
});

// Rate a movie
router.post('/:id/rate', authMiddleware, async (req, res) => {
  try {
    const movieId = req.params.id;
    const userId = req.user.id;
    const { score } = req.body;

    if (score < 1 || score > 5) {
      return res.status(400).json({ error: 'Score must be 1-5' });
    }

    // Check if movie exists
    const movie = await Movie.findByPk(movieId);
    if (!movie) return res.status(404).json({ error: 'Movie not found' });

    // Upsert rating
    const [rating, created] = await Rating.findOrCreate({
      where: { userId, movieId },
      defaults: { score }
    });

    if (!created) {
      rating.score = score;
      await rating.save();
    }

    res.json({ message: 'Rating saved', rating });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
