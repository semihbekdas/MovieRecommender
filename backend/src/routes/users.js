const express = require('express');
const router = express.Router();
const axios = require('axios');
const cheerio = require('cheerio');
const { User, Movie, Rating, Friendship } = require('../models');
const { Op } = require('sequelize');
const authMiddleware = require('../middleware/authMiddleware');
const { ensureMoviePoster } = require('../services/posterService');
const { getTmdbRating } = require('../services/tmdbService');

// Get current user profile
router.get('/me', authMiddleware, async (req, res) => {
  try {
    const user = await User.findByPk(req.user.id, {
      attributes: { exclude: ['passwordHash'] },
      include: [
        { model: Movie, as: 'Watchlist' },
        { model: Movie, as: 'Favorites' },
        { model: Rating, include: [Movie] }
      ]
    });

    if (!user) return res.status(404).json({ error: 'User not found' });

    const userJson = user.toJSON();

    // Process Watchlist
    if (userJson.Watchlist) {
      await Promise.all(userJson.Watchlist.map(async (movie) => {
        await ensureMoviePoster(movie);
        movie.tmdbRating = await getTmdbRating(movie);
      }));
    }

    // Process Favorites
    if (userJson.Favorites) {
      await Promise.all(userJson.Favorites.map(async (movie) => {
        await ensureMoviePoster(movie);
        movie.tmdbRating = await getTmdbRating(movie);
      }));
    }

    // Process Ratings
    if (userJson.Ratings) {
      await Promise.all(userJson.Ratings.map(async (rating) => {
        if (rating.Movie) {
          await ensureMoviePoster(rating.Movie);
          rating.Movie.tmdbRating = await getTmdbRating(rating.Movie);
        }
      }));
    }

    res.json(userJson);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Search users
router.get('/search', authMiddleware, async (req, res) => {
  try {
    const { q } = req.query;
    if (!q) return res.json([]);
    
    const users = await User.findAll({
      where: {
        username: { [Op.like]: `%${q}%` }
      },
      attributes: ['id', 'username'],
      limit: 10
    });
    res.json(users);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Get specific user profile by ID or Username
router.get('/:identifier', authMiddleware, async (req, res) => {
  try {
    const { identifier } = req.params;
    const requesterId = req.user.id;
    
    let targetId;
    // Check if identifier is numeric (ID) or string (username)
    if (/^\d+$/.test(identifier)) {
      targetId = parseInt(identifier);
    } else {
      const userByUsername = await User.findOne({ where: { username: identifier } });
      if (!userByUsername) {
        return res.status(404).json({ error: 'User not found' });
      }
      targetId = userByUsername.id;
    }
    
    // Check if users are friends
    let isFriend = false;
    if (requesterId === targetId) {
      isFriend = true;
    } else {
      const friendship = await Friendship.findOne({
        where: {
          status: 'accepted',
          [Op.or]: [
            { requesterId: requesterId, addresseeId: targetId },
            { requesterId: targetId, addresseeId: requesterId }
          ]
        }
      });
      if (friendship) isFriend = true;
    }

    // Build query
    const include = [];
    if (isFriend) {
      include.push({ model: Movie, as: 'Watchlist' });
      include.push({ model: Movie, as: 'Favorites' });
      include.push({ model: Rating, include: [Movie] });
    }

    const user = await User.findByPk(targetId, {
      attributes: { exclude: ['passwordHash', 'email'] },
      include: include
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Return user data with an extra flag for frontend
    const userData = user.toJSON();
    userData.isFriend = isFriend;

    // Process Watchlist
    if (userData.Watchlist) {
      await Promise.all(userData.Watchlist.map(async (movie) => {
        await ensureMoviePoster(movie);
        movie.tmdbRating = await getTmdbRating(movie);
      }));
    }

    // Process Favorites
    if (userData.Favorites) {
      await Promise.all(userData.Favorites.map(async (movie) => {
        await ensureMoviePoster(movie);
        movie.tmdbRating = await getTmdbRating(movie);
      }));
    }

    // Process Ratings
    if (userData.Ratings) {
      await Promise.all(userData.Ratings.map(async (rating) => {
        if (rating.Movie) {
          await ensureMoviePoster(rating.Movie);
          rating.Movie.tmdbRating = await getTmdbRating(rating.Movie);
        }
      }));
    }

    res.json(userData);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Update user profile
router.put('/me', authMiddleware, async (req, res) => {
  try {
    const { firstName, lastName, profilePicture, imdbProfileUrl } = req.body;
    const user = await User.findByPk(req.user.id);
    
    if (firstName) user.firstName = firstName;
    if (lastName) user.lastName = lastName;
    if (profilePicture) user.profilePicture = profilePicture;
    if (imdbProfileUrl) user.imdbProfileUrl = imdbProfileUrl;
    
    await user.save();
    
    res.json({ 
      id: user.id, 
      username: user.username, 
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      profilePicture: user.profilePicture,
      imdbProfileUrl: user.imdbProfileUrl
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Add to Watchlist
router.post('/me/watchlist', authMiddleware, async (req, res) => {
  try {
    const { movieId } = req.body;
    const user = await User.findByPk(req.user.id);
    const movie = await Movie.findByPk(movieId);
    
    if (!movie) return res.status(404).json({ error: 'Movie not found' });
    
    await user.addWatchlist(movie);
    res.json({ message: 'Added to watchlist' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Remove from Watchlist
router.delete('/me/watchlist/:movieId', authMiddleware, async (req, res) => {
  try {
    const { movieId } = req.params;
    const user = await User.findByPk(req.user.id);
    const movie = await Movie.findByPk(movieId);
    
    if (!movie) return res.status(404).json({ error: 'Movie not found' });
    
    await user.removeWatchlist(movie);
    res.json({ message: 'Removed from watchlist' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Add to Favorites
router.post('/me/favorites', authMiddleware, async (req, res) => {
  try {
    const { movieId } = req.body;
    const user = await User.findByPk(req.user.id);
    const movie = await Movie.findByPk(movieId);
    
    if (!movie) return res.status(404).json({ error: 'Movie not found' });
    
    await user.addFavorites(movie);
    res.json({ message: 'Added to favorites' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Remove from Favorites
router.delete('/me/favorites/:movieId', authMiddleware, async (req, res) => {
  try {
    const { movieId } = req.params;
    const user = await User.findByPk(req.user.id);
    const movie = await Movie.findByPk(movieId);
    
    if (!movie) return res.status(404).json({ error: 'Movie not found' });
    
    await user.removeFavorites(movie);
    res.json({ message: 'Removed from favorites' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});



module.exports = router;
