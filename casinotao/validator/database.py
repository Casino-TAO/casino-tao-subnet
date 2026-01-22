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

from casinotao.core.const import DB_PATH, CASINOTAO_CONTRACT_ADDRESS


def _get_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Initialize the database tables."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Snapshots table - saved when weights are committed
    # Check if we need to migrate old table (add contract_address column)
    cursor.execute("PRAGMA table_info(snapshots)")
    snapshot_columns = [col[1] for col in cursor.fetchall()]
    
    if 'contract_address' not in snapshot_columns and len(snapshot_columns) > 0:
        # Old table exists without contract_address - add column
        bt.logging.info("Migrating snapshots table: adding contract_address column")
        cursor.execute('ALTER TABLE snapshots ADD COLUMN contract_address TEXT')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_address TEXT,
            block_number INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_miners INTEGER,
            total_volume REAL,
            scores_json TEXT,
            volumes_json TEXT
        )
    ''')
    
    # Miner data table - current state of each miner
    # Check if we need to migrate old table (add contract_address column)
    cursor.execute("PRAGMA table_info(miner_data)")
    miner_columns = [col[1] for col in cursor.fetchall()]
    
    if 'contract_address' not in miner_columns and len(miner_columns) > 0:
        # Old table exists without contract_address - drop and recreate
        bt.logging.info("Migrating miner_data table: adding contract_address column")
        cursor.execute('DROP TABLE IF EXISTS miner_data')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS miner_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_address TEXT NOT NULL,
            uid INTEGER NOT NULL,
            hotkey TEXT NOT NULL,
            coldkey TEXT NOT NULL,
            evm_address TEXT,
            daily_volumes_json TEXT,
            weighted_volume REAL DEFAULT 0,
            score REAL DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(contract_address, uid)
        )
    ''')
    
    # Bet events cache - to avoid re-querying blockchain
    # Check if we need to migrate old table (add contract_address column)
    cursor.execute("PRAGMA table_info(bet_events)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'contract_address' not in columns and len(columns) > 0:
        # Old table exists without contract_address - drop and recreate
        # Old data is from different contract anyway
        bt.logging.info("Migrating bet_events table: adding contract_address column")
        cursor.execute('DROP TABLE IF EXISTS bet_events')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bet_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_address TEXT NOT NULL,
            evm_address TEXT NOT NULL,
            game_id INTEGER,
            amount REAL,
            side INTEGER,
            block_number INTEGER,
            timestamp INTEGER,
            UNIQUE(contract_address, evm_address, game_id, block_number, side)
        )
    ''')
    
    # Index for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_bet_events_contract_address 
        ON bet_events(contract_address, evm_address)
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
    miner_details: Optional[Dict[int, dict]] = None,
    contract_address: str = None
):
    """
    Save a snapshot when weights are committed.
    
    Args:
        block_number: Current block number
        scores: Dict of UID -> score
        volumes: Dict of UID -> weighted volume
        miner_details: Optional dict with additional miner info
        contract_address: Contract address (defaults to current)
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    # Convert int keys to strings for JSON
    scores_json = json.dumps({str(k): v for k, v in scores.items()})
    volumes_json = json.dumps({str(k): v for k, v in volumes.items()})
    
    cursor.execute('''
        INSERT INTO snapshots (contract_address, block_number, total_miners, total_volume, scores_json, volumes_json)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        contract_addr,
        block_number,
        len([s for s in scores.values() if s > 0]),
        sum(volumes.values()),
        scores_json,
        volumes_json
    ))
    
    conn.commit()
    conn.close()
    bt.logging.info(f"Snapshot saved at block {block_number} for contract {contract_addr[:10]}...")


def get_latest_snapshot(contract_address: str = None) -> Optional[dict]:
    """Get the most recent snapshot for the current contract."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    cursor.execute('''
        SELECT block_number, timestamp, total_miners, total_volume, scores_json, volumes_json
        FROM snapshots WHERE contract_address = ? ORDER BY id DESC LIMIT 1
    ''', (contract_addr,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'block_number': row[0],
            'timestamp': row[1],
            'total_miners': row[2],
            'total_volume': row[3],
            'scores': json.loads(row[4]) if row[4] else {},
            'volumes': json.loads(row[5]) if row[5] else {}
        }
    return None


def get_snapshots(limit: int = 100, contract_address: str = None) -> List[dict]:
    """Get recent snapshots (summary only) for the current contract."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    cursor.execute('''
        SELECT block_number, timestamp, total_miners, total_volume
        FROM snapshots WHERE contract_address = ? ORDER BY id DESC LIMIT ?
    ''', (contract_addr, limit))
    
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


def get_snapshot_by_block(block_number: int, contract_address: str = None) -> Optional[dict]:
    """Get a specific snapshot by block number for the current contract."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    cursor.execute('''
        SELECT block_number, timestamp, total_miners, total_volume, scores_json, volumes_json
        FROM snapshots WHERE contract_address = ? AND block_number = ?
    ''', (contract_addr, block_number))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'block_number': row[0],
            'timestamp': row[1],
            'total_miners': row[2],
            'total_volume': row[3],
            'scores': json.loads(row[4]) if row[4] else {},
            'volumes': json.loads(row[5]) if row[5] else {}
        }
    return None


def update_miner_data(
    uid: int,
    hotkey: str,
    coldkey: str,
    evm_address: Optional[str],
    daily_volumes: List[float],
    weighted_volume: float,
    score: float,
    contract_address: str = None
):
    """Update or insert miner data for the current contract."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    # Check if record exists for this contract + uid
    cursor.execute(
        'SELECT id FROM miner_data WHERE contract_address = ? AND uid = ?',
        (contract_addr, uid)
    )
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute('''
            UPDATE miner_data 
            SET hotkey = ?, coldkey = ?, evm_address = ?, daily_volumes_json = ?, 
                weighted_volume = ?, score = ?, last_updated = CURRENT_TIMESTAMP
            WHERE contract_address = ? AND uid = ?
        ''', (
            hotkey, coldkey, evm_address, json.dumps(daily_volumes),
            weighted_volume, score, contract_addr, uid
        ))
    else:
        cursor.execute('''
            INSERT INTO miner_data 
            (contract_address, uid, hotkey, coldkey, evm_address, daily_volumes_json, weighted_volume, score, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            contract_addr, uid, hotkey, coldkey, evm_address,
            json.dumps(daily_volumes), weighted_volume, score
        ))
    
    conn.commit()
    conn.close()


def get_miner_data(uid: int, contract_address: str = None) -> Optional[dict]:
    """Get miner data by UID for the current contract."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    cursor.execute('''
        SELECT uid, hotkey, coldkey, evm_address, daily_volumes_json, weighted_volume, score, last_updated
        FROM miner_data WHERE contract_address = ? AND uid = ?
    ''', (contract_addr, uid))
    
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


def get_all_miner_data(contract_address: str = None) -> List[dict]:
    """Get all miner data for the current contract."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    cursor.execute('''
        SELECT uid, hotkey, coldkey, evm_address, daily_volumes_json, weighted_volume, score, last_updated
        FROM miner_data WHERE contract_address = ? ORDER BY score DESC
    ''', (contract_addr,))
    
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
    timestamp: int,
    contract_address: str = None
):
    """Cache a bet event to avoid re-querying."""
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO bet_events 
            (contract_address, evm_address, game_id, amount, side, block_number, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (contract_addr, evm_address, game_id, amount, side, block_number, timestamp))
        conn.commit()
    except Exception as e:
        bt.logging.debug(f"Error caching bet event: {e}")
    finally:
        conn.close()


def get_cached_bet_events(evm_address: str, since_timestamp: int, contract_address: str = None) -> List[dict]:
    """Get cached bet events for an address since a given timestamp.
    
    Only returns events from the specified contract (defaults to current contract).
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    # Use current contract address if not specified
    contract_addr = contract_address or CASINOTAO_CONTRACT_ADDRESS
    
    cursor.execute('''
        SELECT game_id, amount, side, block_number, timestamp
        FROM bet_events 
        WHERE contract_address = ? AND evm_address = ? AND timestamp >= ?
        ORDER BY timestamp DESC
    ''', (contract_addr, evm_address, since_timestamp))
    
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


# ==================== DATA CLEANUP FUNCTIONS ====================

def clear_contract_data(contract_address: str = None, clear_all_except_current: bool = False):
    """
    Clear cached data for a specific contract or all old contracts.
    
    Args:
        contract_address: Specific contract to clear (if None and clear_all_except_current=True,
                          clears all data NOT from current contract)
        clear_all_except_current: If True, clears data from all contracts except current
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    if clear_all_except_current:
        # Clear data from all contracts except the current one
        current_contract = CASINOTAO_CONTRACT_ADDRESS
        
        cursor.execute('DELETE FROM bet_events WHERE contract_address != ?', (current_contract,))
        bet_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM miner_data WHERE contract_address != ?', (current_contract,))
        miner_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM snapshots WHERE contract_address != ? AND contract_address IS NOT NULL', 
                      (current_contract,))
        snapshot_deleted = cursor.rowcount
        
        bt.logging.info(
            f"Cleared old contract data: {bet_deleted} bet events, "
            f"{miner_deleted} miner records, {snapshot_deleted} snapshots"
        )
    elif contract_address:
        # Clear data for specific contract
        cursor.execute('DELETE FROM bet_events WHERE contract_address = ?', (contract_address,))
        bet_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM miner_data WHERE contract_address = ?', (contract_address,))
        miner_deleted = cursor.rowcount
        
        cursor.execute('DELETE FROM snapshots WHERE contract_address = ?', (contract_address,))
        snapshot_deleted = cursor.rowcount
        
        bt.logging.info(
            f"Cleared data for contract {contract_address[:10]}...: "
            f"{bet_deleted} bet events, {miner_deleted} miner records, {snapshot_deleted} snapshots"
        )
    
    conn.commit()
    conn.close()


def get_contract_stats() -> Dict[str, dict]:
    """
    Get statistics about data stored for each contract.
    
    Returns:
        Dict mapping contract_address -> stats dict
    """
    conn = _get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # Bet events by contract
    cursor.execute('''
        SELECT contract_address, COUNT(*) as count, SUM(amount) as total_amount
        FROM bet_events GROUP BY contract_address
    ''')
    for row in cursor.fetchall():
        contract = row[0] or 'unknown'
        stats[contract] = {
            'bet_events': row[1],
            'total_bet_amount': row[2] or 0
        }
    
    # Miner data by contract
    cursor.execute('''
        SELECT contract_address, COUNT(*) as count
        FROM miner_data GROUP BY contract_address
    ''')
    for row in cursor.fetchall():
        contract = row[0] or 'unknown'
        if contract not in stats:
            stats[contract] = {}
        stats[contract]['miner_records'] = row[1]
    
    # Snapshots by contract
    cursor.execute('''
        SELECT contract_address, COUNT(*) as count
        FROM snapshots GROUP BY contract_address
    ''')
    for row in cursor.fetchall():
        contract = row[0] or 'unknown'
        if contract not in stats:
            stats[contract] = {}
        stats[contract]['snapshots'] = row[1]
    
    conn.close()
    return stats
