# The MIT License (MIT)
# Copyright © 2025 Casino TAO

"""
Database module for Casino TAO validator.
Handles snapshots and miner volume tracking using SQLite.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import bittensor as bt

from casinotao.core.const import DB_PATH


def _get_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Initialize the database tables."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Snapshots table - saved when weights are committed
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_number INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_miners INTEGER,
            total_volume REAL,
            scores_json TEXT,
            volumes_json TEXT
        )
    ''')
    
    # Miner data table - current state of each miner
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS miner_data (
            uid INTEGER PRIMARY KEY,
            hotkey TEXT NOT NULL,
            coldkey TEXT NOT NULL,
            evm_address TEXT,
            daily_volumes_json TEXT,
            weighted_volume REAL DEFAULT 0,
            score REAL DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bet events cache - to avoid re-querying blockchain
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bet_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evm_address TEXT NOT NULL,
            game_id INTEGER,
            amount REAL,
            side INTEGER,
            block_number INTEGER,
            timestamp INTEGER,
            UNIQUE(evm_address, game_id, block_number, side)
        )
    ''')
    
    # Index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_bet_events_address 
        ON bet_events(evm_address)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_bet_events_timestamp 
        ON bet_events(timestamp)
    ''')
    
    # Wallet mappings table - coldkey to EVM address mappings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallet_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coldkey TEXT NOT NULL UNIQUE,
            evm_address TEXT NOT NULL,
            signature TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            verified_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_wallet_mappings_coldkey 
        ON wallet_mappings(coldkey)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_wallet_mappings_evm 
        ON wallet_mappings(evm_address)
    ''')
    
    conn.commit()
    conn.close()
    bt.logging.info("Database initialized successfully")


def save_snapshot(
    block_number: int, 
    scores: Dict[int, float], 
    volumes: Dict[int, float],
    miner_details: Optional[Dict[int, dict]] = None
):
    """
    Save a snapshot when weights are committed.
    
    Args:
        block_number: Current block number
        scores: Dict of UID -> score
        volumes: Dict of UID -> weighted volume
        miner_details: Optional dict with additional miner info
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Convert int keys to strings for JSON
    scores_json = json.dumps({str(k): v for k, v in scores.items()})
    volumes_json = json.dumps({str(k): v for k, v in volumes.items()})
    
    cursor.execute('''
        INSERT INTO snapshots (block_number, total_miners, total_volume, scores_json, volumes_json)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        block_number,
        len([s for s in scores.values() if s > 0]),
        sum(volumes.values()),
        scores_json,
        volumes_json
    ))
    
    conn.commit()
    conn.close()
    bt.logging.info(f"Snapshot saved at block {block_number}")


def get_latest_snapshot() -> Optional[dict]:
    """Get the most recent snapshot."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT block_number, timestamp, total_miners, total_volume, scores_json, volumes_json
        FROM snapshots ORDER BY id DESC LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'block_number': row[0],
            'timestamp': row[1],
            'total_miners': row[2],
            'total_volume': row[3],
            'scores': json.loads(row[4]),
            'volumes': json.loads(row[5])
        }
    return None


def get_snapshots(limit: int = 100) -> List[dict]:
    """Get recent snapshots (summary only)."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT block_number, timestamp, total_miners, total_volume
        FROM snapshots ORDER BY id DESC LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'block_number': r[0],
            'timestamp': r[1],
            'total_miners': r[2],
            'total_volume': r[3]
        }
        for r in rows
    ]


def get_snapshot_by_block(block_number: int) -> Optional[dict]:
    """Get a specific snapshot by block number."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT block_number, timestamp, total_miners, total_volume, scores_json, volumes_json
        FROM snapshots WHERE block_number = ?
    ''', (block_number,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'block_number': row[0],
            'timestamp': row[1],
            'total_miners': row[2],
            'total_volume': row[3],
            'scores': json.loads(row[4]),
            'volumes': json.loads(row[5])
        }
    return None


def update_miner_data(
    uid: int,
    hotkey: str,
    coldkey: str,
    evm_address: Optional[str],
    daily_volumes: List[float],
    weighted_volume: float,
    score: float
):
    """Update or insert miner data."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO miner_data 
        (uid, hotkey, coldkey, evm_address, daily_volumes_json, weighted_volume, score, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        uid,
        hotkey,
        coldkey,
        evm_address,
        json.dumps(daily_volumes),
        weighted_volume,
        score
    ))
    
    conn.commit()
    conn.close()


def get_miner_data(uid: int) -> Optional[dict]:
    """Get miner data by UID."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT uid, hotkey, coldkey, evm_address, daily_volumes_json, weighted_volume, score, last_updated
        FROM miner_data WHERE uid = ?
    ''', (uid,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'uid': row[0],
            'hotkey': row[1],
            'coldkey': row[2],
            'evm_address': row[3],
            'daily_volumes': json.loads(row[4]) if row[4] else [],
            'weighted_volume': row[5],
            'score': row[6],
            'last_updated': row[7]
        }
    return None


def get_all_miner_data() -> List[dict]:
    """Get all miner data."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT uid, hotkey, coldkey, evm_address, daily_volumes_json, weighted_volume, score, last_updated
        FROM miner_data ORDER BY score DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'uid': r[0],
            'hotkey': r[1],
            'coldkey': r[2],
            'evm_address': r[3],
            'daily_volumes': json.loads(r[4]) if r[4] else [],
            'weighted_volume': r[5],
            'score': r[6],
            'last_updated': r[7]
        }
        for r in rows
    ]


def cache_bet_event(
    evm_address: str,
    game_id: int,
    amount: float,
    side: int,
    block_number: int,
    timestamp: int
):
    """Cache a bet event to avoid re-querying."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO bet_events 
            (evm_address, game_id, amount, side, block_number, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (evm_address, game_id, amount, side, block_number, timestamp))
        conn.commit()
    except Exception as e:
        bt.logging.debug(f"Error caching bet event: {e}")
    finally:
        conn.close()


def get_cached_bet_events(evm_address: str, since_timestamp: int) -> List[dict]:
    """Get cached bet events for an address since a given timestamp."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT game_id, amount, side, block_number, timestamp
        FROM bet_events 
        WHERE evm_address = ? AND timestamp >= ?
        ORDER BY timestamp DESC
    ''', (evm_address, since_timestamp))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'game_id': r[0],
            'amount': r[1],
            'side': r[2],
            'block_number': r[3],
            'timestamp': r[4]
        }
        for r in rows
    ]


def cleanup_old_events(days: int = 14):
    """Remove bet events older than specified days."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cutoff = int(datetime.utcnow().timestamp()) - (days * 86400)
    
    cursor.execute('DELETE FROM bet_events WHERE timestamp < ?', (cutoff,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    if deleted > 0:
        bt.logging.info(f"Cleaned up {deleted} old bet events")


# ==================== WALLET MAPPING FUNCTIONS ====================

def save_wallet_mapping(
    coldkey: str,
    evm_address: str,
    signature: str,
    message: str,
    timestamp: int
) -> bool:
    """
    Save or update a wallet mapping (coldkey -> EVM address).
    
    Args:
        coldkey: Bittensor coldkey (SS58 format)
        evm_address: EVM wallet address
        signature: Hex signature (without 0x prefix)
        message: The signed message
        timestamp: Unix timestamp in milliseconds
        
    Returns:
        True if saved successfully, False otherwise
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO wallet_mappings 
            (coldkey, evm_address, signature, message, timestamp, verified_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            coldkey,
            evm_address.lower(),  # Normalize EVM address to lowercase
            signature,
            message,
            timestamp
        ))
        conn.commit()
        bt.logging.info(f"Wallet mapping saved: {coldkey[:10]}... -> {evm_address[:10]}...")
        return True
    except Exception as e:
        bt.logging.error(f"Failed to save wallet mapping: {e}")
        return False
    finally:
        conn.close()


def get_wallet_mapping(coldkey: str) -> Optional[dict]:
    """
    Get wallet mapping for a coldkey.
    
    Args:
        coldkey: Bittensor coldkey (SS58 format)
        
    Returns:
        Dict with mapping info or None if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT coldkey, evm_address, signature, message, timestamp, verified_at
        FROM wallet_mappings WHERE coldkey = ?
    ''', (coldkey,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'coldkey': row[0],
            'evm_address': row[1],
            'signature': row[2],
            'message': row[3],
            'timestamp': row[4],
            'verified_at': row[5]
        }
    return None


def get_evm_address_for_coldkey(coldkey: str) -> Optional[str]:
    """
    Get the EVM address mapped to a coldkey.
    
    Args:
        coldkey: Bittensor coldkey (SS58 format)
        
    Returns:
        EVM address or None if not mapped
    """
    mapping = get_wallet_mapping(coldkey)
    return mapping['evm_address'] if mapping else None


def get_all_wallet_mappings() -> List[dict]:
    """Get all wallet mappings."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT coldkey, evm_address, timestamp, verified_at
        FROM wallet_mappings ORDER BY verified_at DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'coldkey': r[0],
            'evm_address': r[1],
            'timestamp': r[2],
            'verified_at': r[3]
        }
        for r in rows
    ]


def delete_wallet_mapping(coldkey: str) -> bool:
    """
    Delete a wallet mapping.
    
    Args:
        coldkey: Bittensor coldkey to remove mapping for
        
    Returns:
        True if deleted, False if not found
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM wallet_mappings WHERE coldkey = ?', (coldkey,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted
