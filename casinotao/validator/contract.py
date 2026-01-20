# The MIT License (MIT)
# Copyright © 2025 Casino TAO

"""
Contract interaction module for Casino TAO validator.
Queries the casinotao smart contract on Bittensor EVM.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import bittensor as bt

try:
    from web3 import Web3
    from web3.exceptions import ContractLogicError
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    bt.logging.warning("web3 not installed. Install with: pip install web3")

from casinotao.core.const import (
    CASINOTAO_CONTRACT_ADDRESS,
    BITTENSOR_EVM_RPC,
    BLOCKS_PER_DAY,
    TIME_DECAY_WEIGHTS,
)
from casinotao.validator.database import cache_bet_event, get_cached_bet_events


# casinotao ABI - only the functions/events we need
casinotao_ABI = [
    # getUserStats function
    {
        "inputs": [{"name": "_user", "type": "address"}],
        "name": "getUserStats",
        "outputs": [
            {"name": "totalBets", "type": "uint256"},
            {"name": "totalWins", "type": "uint256"},
            {"name": "totalWinnings", "type": "uint256"},
            {"name": "totalLosses", "type": "uint256"},
            {"name": "referralEarnings", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    # BetPlaced event
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "gameId", "type": "uint256"},
            {"indexed": True, "name": "bettor", "type": "address"},
            {"indexed": False, "name": "side", "type": "uint8"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": False, "name": "newPoolTotal", "type": "uint256"},
            {"indexed": False, "name": "referrer", "type": "address"}
        ],
        "name": "BetPlaced",
        "type": "event"
    }
]


class ContractClient:
    """Client for interacting with the casinotao contract."""
    
    def __init__(self, rpc_url: str = None, contract_address: str = None):
        if not WEB3_AVAILABLE:
            raise ImportError("web3 is required. Install with: pip install web3")
        
        self.rpc_url = rpc_url or BITTENSOR_EVM_RPC
        self.contract_address = contract_address or CASINOTAO_CONTRACT_ADDRESS
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address),
            abi=casinotao_ABI
        )
        
        bt.logging.info(f"ContractClient initialized: {self.contract_address}")
    
    def is_connected(self) -> bool:
        """Check if connected to the RPC."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False
    
    def get_current_block(self) -> int:
        """Get the current block number."""
        return self.w3.eth.block_number
    
    def get_user_stats(self, address: str) -> Optional[Dict]:
        """
        Get user stats from the contract.
        
        Args:
            address: EVM address to query
            
        Returns:
            Dict with totalBets, totalWins, totalWinnings, totalLosses, referralEarnings
        """
        try:
            checksum_address = Web3.to_checksum_address(address)
            stats = self.contract.functions.getUserStats(checksum_address).call()
            
            return {
                'total_bets': stats[0],
                'total_wins': stats[1],
                'total_winnings': stats[2],  # In wei
                'total_losses': stats[3],
                'referral_earnings': stats[4]  # In wei
            }
        except ContractLogicError as e:
            bt.logging.debug(f"Contract error for {address}: {e}")
            return None
        except Exception as e:
            bt.logging.warning(f"Error getting user stats for {address}: {e}")
            return None
    
    def get_bet_events(
        self, 
        address: str, 
        from_block: int, 
        to_block: int = None
    ) -> List[Dict]:
        """
        Get BetPlaced events for an address within a block range.
        
        Args:
            address: EVM address to query
            from_block: Starting block
            to_block: Ending block (default: latest)
            
        Returns:
            List of bet event dicts
        """
        try:
            checksum_address = Web3.to_checksum_address(address)
            to_block_val = to_block if to_block else self.w3.eth.block_number
            
            # Get the event topic (BetPlaced event signature hash)
            # BetPlaced(uint256 indexed gameId, address indexed bettor, uint8 side, uint256 amount, uint256 newPoolTotal, address referrer)
            event_signature = self.w3.keccak(text="BetPlaced(uint256,address,uint8,uint256,uint256,address)")
            
            # Pad the address to 32 bytes for indexed parameter filtering
            address_topic = '0x' + checksum_address[2:].lower().zfill(64)
            
            # Use eth.get_logs directly - most reliable approach
            logs = self.w3.eth.get_logs({
                'fromBlock': from_block,
                'toBlock': to_block_val,
                'address': self.contract_address,
                'topics': [
                    event_signature.hex(),  # Event signature
                    None,                   # gameId (indexed, but we want all)
                    address_topic           # bettor (indexed)
                ]
            })
            
            bet_events = []
            for log in logs:
                try:
                    # Decode the event data
                    decoded = self.contract.events.BetPlaced().process_log(log)
                    
                    # Get block timestamp
                    try:
                        block = self.w3.eth.get_block(log['blockNumber'])
                        timestamp = block['timestamp']
                    except Exception:
                        timestamp = int(datetime.utcnow().timestamp())
                    
                    bet_event = {
                        'game_id': decoded['args']['gameId'],
                        'bettor': decoded['args']['bettor'],
                        'side': decoded['args']['side'],
                        'amount': decoded['args']['amount'],  # In wei
                        'block_number': log['blockNumber'],
                        'timestamp': timestamp,
                        'tx_hash': log['transactionHash'].hex()
                    }
                    bet_events.append(bet_event)
                    
                    # Cache the event
                    cache_bet_event(
                        evm_address=address.lower(),
                        game_id=bet_event['game_id'],
                        amount=float(self.w3.from_wei(bet_event['amount'], 'ether')),
                        side=bet_event['side'],
                        block_number=bet_event['block_number'],
                        timestamp=bet_event['timestamp']
                    )
                except Exception as decode_err:
                    bt.logging.debug(f"Error decoding log: {decode_err}")
                    continue
            
            return bet_events
            
        except Exception as e:
            bt.logging.warning(f"Error getting bet events for {address}: {e}")
            return []
    
    def get_bets_last_7_days(self, address: str) -> List[Dict]:
        """
        Get all bets from the last 7 days for an address.
        
        Args:
            address: EVM address to query
            
        Returns:
            List of bet event dicts
        """
        try:
            current_block = self.get_current_block()
            from_block = max(0, current_block - (BLOCKS_PER_DAY * 7))
            
            # First check cache
            seven_days_ago = int((datetime.utcnow() - timedelta(days=7)).timestamp())
            cached_events = get_cached_bet_events(address.lower(), seven_days_ago)
            
            if cached_events:
                # Get only new events since last cached
                last_cached_block = max(e['block_number'] for e in cached_events)
                if last_cached_block >= current_block - 100:  # Within 100 blocks, use cache
                    bt.logging.debug(f"Using cached events for {address[:10]}...")
                    return cached_events
                from_block = last_cached_block + 1
            
            # Query new events from chain
            new_events = self.get_bet_events(address, from_block)
            
            # Combine cached and new events
            all_events = cached_events + [
                {
                    'game_id': e['game_id'],
                    'amount': float(self.w3.from_wei(e['amount'], 'ether')),
                    'side': e['side'],
                    'block_number': e['block_number'],
                    'timestamp': e['timestamp']
                }
                for e in new_events
            ]
            
            return all_events
            
        except Exception as e:
            bt.logging.warning(f"Error getting 7-day bets for {address}: {e}")
            return []


def calculate_time_decayed_volume(bet_events: List[Dict]) -> tuple:
    """
    Calculate time-decayed volume from bet events.
    
    Args:
        bet_events: List of bet events with 'timestamp' and 'amount'
        
    Returns:
        Tuple of (weighted_volume, daily_volumes_list)
    """
    now = datetime.utcnow()
    daily_volumes = [0.0] * 7  # [today, yesterday, ..., 6 days ago]
    
    for event in bet_events:
        try:
            event_time = datetime.utcfromtimestamp(event['timestamp'])
            days_ago = (now - event_time).days
            
            if 0 <= days_ago < 7:
                # Amount should already be in TAO (ether units)
                amount = event.get('amount', 0)
                if isinstance(amount, int):
                    # If still in wei, convert
                    amount = amount / 1e18
                daily_volumes[days_ago] += amount
        except Exception as e:
            bt.logging.debug(f"Error processing bet event: {e}")
            continue
    
    # Apply decay weights
    weighted_volume = sum(
        vol * weight 
        for vol, weight in zip(daily_volumes, TIME_DECAY_WEIGHTS)
    )
    
    return weighted_volume, daily_volumes


def get_miner_volume(client: ContractClient, evm_address: str) -> tuple:
    """
    Get time-decayed betting volume for a miner's EVM address.
    
    Args:
        client: ContractClient instance
        evm_address: Miner's EVM address
        
    Returns:
        Tuple of (weighted_volume, daily_volumes)
    """
    if not evm_address:
        return 0.0, [0.0] * 7
    
    try:
        bet_events = client.get_bets_last_7_days(evm_address)
        return calculate_time_decayed_volume(bet_events)
    except Exception as e:
        bt.logging.warning(f"Error getting miner volume: {e}")
        return 0.0, [0.0] * 7


# Singleton client instance
_contract_client: Optional[ContractClient] = None


def get_contract_client() -> ContractClient:
    """Get or create the singleton contract client."""
    global _contract_client
    if _contract_client is None:
        _contract_client = ContractClient()
    return _contract_client
