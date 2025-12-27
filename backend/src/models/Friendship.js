const { DataTypes } = require('sequelize');
const sequelize = require('../config/db');

const Friendship = sequelize.define('Friendship', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  requesterId: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  addresseeId: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  status: {
    type: DataTypes.STRING, // "pending", "accepted", "blocked"
    defaultValue: 'pending',
    allowNull: false
  }
}, {
  timestamps: true
});

module.exports = Friendship;
