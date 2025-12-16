const { DataTypes } = require('sequelize');
const sequelize = require('../config/db');

const Movie = sequelize.define('Movie', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  tmdbId: {
    type: DataTypes.INTEGER,
    allowNull: true,
    unique: true
  },
  title: {
    type: DataTypes.STRING,
    allowNull: false
  },
  year: {
    type: DataTypes.INTEGER,
    allowNull: true
  },
  genres: {
    type: DataTypes.STRING, // Comma-separated or JSON string
    allowNull: true
  },
  actors: {
    type: DataTypes.STRING,
    allowNull: true
  },
  director: {
    type: DataTypes.STRING,
    allowNull: true
  },
  posterUrl: {
    type: DataTypes.STRING,
    allowNull: true
  },
  imdbUrl: {
    type: DataTypes.STRING,
    allowNull: true
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true
  }
}, {
  timestamps: false
});

module.exports = Movie;
