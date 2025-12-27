const express = require('express');
const router = express.Router();
const { User, Friendship } = require('../models');
const authMiddleware = require('../middleware/authMiddleware');
const { Op } = require('sequelize');

// List friends
router.get('/', authMiddleware, async (req, res) => {
  try {
    const userId = req.user.id;
    // Find accepted friendships where user is requester or addressee
    const friendships = await Friendship.findAll({
      where: {
        status: 'accepted',
        [Op.or]: [{ requesterId: userId }, { addresseeId: userId }]
      }
    });

    const friendIds = friendships.map(f => 
      f.requesterId === userId ? f.addresseeId : f.requesterId
    );

    const friends = await User.findAll({
      where: { id: friendIds },
      attributes: ['id', 'username', 'profilePicture']
    });

    res.json(friends);
  } catch (error) {
    res.status(500).json({ error: 'Server error' });
  }
});

// List pending friend requests
router.get('/requests', authMiddleware, async (req, res) => {
  try {
    const userId = req.user.id;
    
    const requests = await Friendship.findAll({
      where: {
        addresseeId: userId,
        status: 'pending'
      },
      include: [
        { model: User, as: 'Requester', attributes: ['id', 'username', 'profilePicture'] }
      ]
    });

    res.json(requests);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Server error' });
  }
});

// Send friend request
router.post('/request', authMiddleware, async (req, res) => {
  try {
    const { addresseeId } = req.body;
    const requesterId = req.user.id;

    if (requesterId === addresseeId) {
      return res.status(400).json({ error: 'Cannot add yourself' });
    }

    const existing = await Friendship.findOne({
      where: {
        [Op.or]: [
          { requesterId, addresseeId },
          { requesterId: addresseeId, addresseeId: requesterId }
        ]
      }
    });

    if (existing) {
      return res.status(400).json({ error: 'Friendship or request already exists' });
    }

    await Friendship.create({
      requesterId,
      addresseeId,
      status: 'pending'
    });

    res.json({ message: 'Friend request sent' });
  } catch (error) {
    res.status(500).json({ error: 'Server error' });
  }
});

// Accept friend request
router.post('/accept/:id', authMiddleware, async (req, res) => {
  try {
    const friendshipId = req.params.id;
    const userId = req.user.id;

    const friendship = await Friendship.findByPk(friendshipId);
    if (!friendship) return res.status(404).json({ error: 'Not found' });

    if (friendship.addresseeId !== userId) {
      return res.status(403).json({ error: 'Not authorized' });
    }

    friendship.status = 'accepted';
    await friendship.save();

    res.json({ message: 'Friend request accepted' });
  } catch (error) {
    res.status(500).json({ error: 'Server error' });
  }
});

// Remove friend
router.delete('/:friendId', authMiddleware, async (req, res) => {
  try {
    const userId = req.user.id;
    const friendId = parseInt(req.params.friendId);

    console.log(`[DELETE Friend] Request - User: ${userId}, Friend: ${friendId}`);

    if (isNaN(friendId)) {
      console.log('[DELETE Friend] Invalid ID');
      return res.status(400).json({ error: 'Invalid friend ID' });
    }

    // Try to find the friendship first
    const friendship = await Friendship.findOne({
      where: {
        status: 'accepted',
        [Op.or]: [
          { requesterId: userId, addresseeId: friendId },
          { requesterId: friendId, addresseeId: userId }
        ]
      }
    });

    if (!friendship) {
      console.log('[DELETE Friend] Friendship not found in DB');
      return res.status(404).json({ error: 'Friendship not found' });
    }

    console.log(`[DELETE Friend] Found friendship ID: ${friendship.id}. Deleting...`);

    await friendship.destroy();

    console.log('[DELETE Friend] Deleted successfully');
    res.json({ message: 'Friend removed' });
  } catch (error) {
    console.error('[DELETE Friend] Error:', error);
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;
