const User = require('./User');
const Movie = require('./Movie');
const Rating = require('./Rating');
const Friendship = require('./Friendship');

// User <-> Rating
User.hasMany(Rating, { foreignKey: 'userId' });
Rating.belongsTo(User, { foreignKey: 'userId' });

// Movie <-> Rating
Movie.hasMany(Rating, { foreignKey: 'movieId' });
Rating.belongsTo(Movie, { foreignKey: 'movieId' });

// User <-> User (Friendship)
// We need to define this carefully for requester/addressee
User.belongsToMany(User, { 
  as: 'Friends', 
  through: Friendship, 
  foreignKey: 'requesterId',
  otherKey: 'addresseeId'
});

// Explicit associations for Friendship model queries
Friendship.belongsTo(User, { as: 'Requester', foreignKey: 'requesterId' });
Friendship.belongsTo(User, { as: 'Addressee', foreignKey: 'addresseeId' });

// User <-> Movie (Watchlist)
User.belongsToMany(Movie, { as: 'Watchlist', through: 'UserWatchlist' });
Movie.belongsToMany(User, { as: 'WatchlistedBy', through: 'UserWatchlist' });

// User <-> Movie (Favorites)
User.belongsToMany(Movie, { as: 'Favorites', through: 'UserFavorites' });
Movie.belongsToMany(User, { as: 'FavoritedBy', through: 'UserFavorites' });

// Also the reverse relationship if needed, or we can just query Friendship table directly
// For simplicity in this project, we might often query the Friendship model directly to find friends.

module.exports = {
  User,
  Movie,
  Rating,
  Friendship
};
