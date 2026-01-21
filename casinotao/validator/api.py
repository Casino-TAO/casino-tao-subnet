# The MIT License (MIT)
# Copyright © 2025 Casino TAO

"""
API module for Casino TAO validator.
Provides REST endpoints to query validator state, scores, and volumes.
"""

import threading
from typing import Optional
import bittensor as bt

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    bt.logging.warning("fastapi not installed. Install with: pip install fastapi uvicorn")

from casinotao.core.const import API_HOST, API_PORT
from casinotao.validator.database import (
    get_latest_snapshot,
    get_snapshots,
    get_snapshot_by_block,
    get_miner_data,
    get_all_miner_data,
    save_wallet_mapping,
    get_wallet_mapping,
    get_all_wallet_mappings,
)

# Signature verification imports - CRITICAL for security
try:
    from binascii import unhexlify
    from substrateinterface import Keypair
    SIGNATURE_VERIFICATION_AVAILABLE = True
except ImportError as e:
    SIGNATURE_VERIFICATION_AVAILABLE = False
    bt.logging.error(
        f"⚠️  CRITICAL: substrateinterface import failed: {e}. "
        "Wallet mapping endpoint will reject all requests. "
        "Install with: pip install substrateinterface"
    )
except Exception as e:
    SIGNATURE_VERIFICATION_AVAILABLE = False
    bt.logging.error(f"⚠️  CRITICAL: Signature verification setup error: {e}")


# FastAPI app instance
app = None
if FASTAPI_AVAILABLE:
    from pydantic import BaseModel, Field
    
    # Pydantic models for request/response
    class WalletMappingData(BaseModel):
        coldkey: str = Field(..., description="SS58 Bittensor coldkey address")
        evmAddress: str = Field(..., description="EVM wallet address with 0x prefix")
        signature: str = Field(..., description="Hex signature without 0x prefix")
        message: str = Field(..., description="Signed message wrapped in <Bytes>...</Bytes>")
        timestamp: int = Field(..., description="Unix timestamp in milliseconds")
        verified: bool = Field(..., description="UI format validation passed")
    
    class WalletMappingRequest(BaseModel):
        type: str = Field(..., description="Request type, should be 'wallet_mapping'")
        data: WalletMappingData
    
    class WalletMappingResponse(BaseModel):
        success: bool
    
    class ErrorResponse(BaseModel):
        error: str
    
    app = FastAPI(
        title="Casino TAO Validator API",
        description="API for querying Casino TAO validator state, miner scores, and betting volumes",
        version="1.0.0"
    )
    
    # Enable CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _verify_coldkey_signature(coldkey: str, message: str, signature: str) -> bool:
    """
    Verify a Bittensor coldkey signature.
    
    Args:
        coldkey: SS58 coldkey address
        message: The message that was signed (with <Bytes>...</Bytes> wrapper)
        signature: Hex signature without 0x prefix
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Try to import at runtime if not available at module load
        from binascii import unhexlify
        from substrateinterface import Keypair
        
        # Create keypair from SS58 address
        keypair = Keypair(ss58_address=coldkey, ss58_format=42)
        
        # Convert hex signature to bytes
        signature_bytes = unhexlify(signature.encode())
        
        # Verify the signature
        is_valid = keypair.verify(data=message, signature=signature_bytes)
        
        if is_valid:
            bt.logging.info(f"Signature verified for coldkey: {coldkey[:10]}...")
        else:
            bt.logging.warning(f"Invalid signature for coldkey: {coldkey[:10]}...")
        
        return is_valid
        
    except ImportError as e:
        bt.logging.error(f"Signature verification not available ({e}) - REJECTING for security")
        return False  # NEVER accept without verification - security critical
    except Exception as e:
        bt.logging.error(f"Signature verification failed: {e}")
        return False


# Reference to validator instance (set during startup)
_validator_instance = None


def set_validator(validator):
    """Set the validator instance for the API to reference."""
    global _validator_instance
    _validator_instance = validator


def get_validator():
    """Get the validator instance."""
    if _validator_instance is None:
        raise HTTPException(status_code=503, detail="Validator not initialized")
    return _validator_instance


if FASTAPI_AVAILABLE:
    
    @app.get("/", tags=["Health"])
    def root():
        """Root endpoint - service status."""
        return {
            "status": "ok",
            "service": "Casino TAO Validator",
            "version": "1.0.0"
        }
    
    
    @app.get("/health", tags=["Health"])
    def health():
        """Health check endpoint with validator status."""
        validator = get_validator()
        return {
            "status": "healthy",
            "block": validator.block,
            "step": validator.step,
            "netuid": validator.config.netuid,
            "uid": validator.uid
        }
    
    
    @app.get("/info", tags=["Health"])
    def info():
        """Get validator information."""
        validator = get_validator()
        return {
            "netuid": validator.config.netuid,
            "uid": validator.uid,
            "hotkey": validator.wallet.hotkey.ss58_address,
            "block": validator.block,
            "step": validator.step,
            "total_miners": validator.metagraph.n,
            "network": validator.subtensor.chain_endpoint
        }
    
    
    @app.get("/scores", tags=["Scores"])
    def get_current_scores(
        min_score: float = Query(0.0, description="Minimum score to include")
    ):
        """Get current miner scores."""
        validator = get_validator()
        
        scores = {}
        for uid in range(len(validator.scores)):
            score = float(validator.scores[uid])
            if score >= min_score:
                scores[uid] = {
                    'uid': uid,
                    'hotkey': validator.metagraph.hotkeys[uid],
                    'coldkey': validator.metagraph.coldkeys[uid],
                    'score': score
                }
        
        return {
            'block': validator.block,
            'total_miners': len(scores),
            'scores': scores
        }
    
    
    @app.get("/scores/{uid}", tags=["Scores"])
    def get_miner_score(uid: int):
        """Get specific miner's score and details."""
        validator = get_validator()
        
        if uid >= len(validator.scores) or uid < 0:
            raise HTTPException(status_code=404, detail=f"Miner UID {uid} not found")
        
        # Get additional data from database
        miner_db_data = get_miner_data(uid)
        
        response = {
            'uid': uid,
            'hotkey': validator.metagraph.hotkeys[uid],
            'coldkey': validator.metagraph.coldkeys[uid],
            'score': float(validator.scores[uid]),
            'block': validator.block
        }
        
        if miner_db_data:
            response.update({
                'evm_address': miner_db_data.get('evm_address'),
                'daily_volumes': miner_db_data.get('daily_volumes', []),
                'weighted_volume': miner_db_data.get('weighted_volume', 0),
                'last_updated': miner_db_data.get('last_updated')
            })
        
        return response
    
    
    @app.get("/volumes", tags=["Volumes"])
    def get_current_volumes():
        """Get current miner volumes (time-decayed)."""
        validator = get_validator()
        
        # Access cached volumes from validator
        volumes = getattr(validator, 'miner_volumes', {})
        daily_volumes = getattr(validator, 'miner_daily_volumes', {})
        
        return {
            'block': validator.block,
            'total_volume': sum(volumes.values()) if volumes else 0,
            'miners_with_volume': len([v for v in volumes.values() if v > 0]),
            'volumes': volumes,
            'daily_breakdown': daily_volumes
        }
    
    
    @app.get("/volumes/{uid}", tags=["Volumes"])
    def get_miner_volume(uid: int):
        """Get specific miner's volume details."""
        validator = get_validator()
        
        if uid >= validator.metagraph.n or uid < 0:
            raise HTTPException(status_code=404, detail=f"Miner UID {uid} not found")
        
        miner_data = get_miner_data(uid)
        
        if not miner_data:
            return {
                'uid': uid,
                'weighted_volume': 0,
                'daily_volumes': [0] * 7,
                'message': 'No volume data available'
            }
        
        return {
            'uid': uid,
            'evm_address': miner_data.get('evm_address'),
            'weighted_volume': miner_data.get('weighted_volume', 0),
            'daily_volumes': miner_data.get('daily_volumes', []),
            'last_updated': miner_data.get('last_updated')
        }
    
    
    @app.get("/snapshots", tags=["Snapshots"])
    def get_weight_snapshots(
        limit: int = Query(50, ge=1, le=500, description="Number of snapshots to return")
    ):
        """Get historical weight snapshots (summary only)."""
        snapshots = get_snapshots(limit)
        return {
            'count': len(snapshots),
            'snapshots': snapshots
        }
    
    
    @app.get("/snapshots/latest", tags=["Snapshots"])
    def get_latest_weight_snapshot():
        """Get the most recent weight snapshot with full details."""
        snapshot = get_latest_snapshot()
        if not snapshot:
            raise HTTPException(status_code=404, detail="No snapshots found")
        return snapshot
    
    
    @app.get("/snapshots/{block_number}", tags=["Snapshots"])
    def get_snapshot_at_block(block_number: int):
        """Get snapshot at a specific block number."""
        snapshot = get_snapshot_by_block(block_number)
        if not snapshot:
            raise HTTPException(
                status_code=404, 
                detail=f"No snapshot found for block {block_number}"
            )
        return snapshot
    
    
    @app.get("/leaderboard", tags=["Leaderboard"])
    def get_leaderboard(
        limit: int = Query(20, ge=1, le=100, description="Number of miners to return")
    ):
        """Get top miners by score."""
        validator = get_validator()
        
        # Sort miners by score
        scored_miners = []
        for uid in range(len(validator.scores)):
            score = float(validator.scores[uid])
            if score > 0:
                scored_miners.append({
                    'rank': 0,  # Will be set after sorting
                    'uid': uid,
                    'coldkey': validator.metagraph.coldkeys[uid],
                    'score': score
                })
        
        scored_miners.sort(key=lambda x: x['score'], reverse=True)
        
        # Add ranks
        for i, miner in enumerate(scored_miners[:limit]):
            miner['rank'] = i + 1
        
        return {
            'block': validator.block,
            'total_active_miners': len(scored_miners),
            'leaderboard': scored_miners[:limit]
        }
    
    
    @app.get("/miners", tags=["Miners"])
    def get_all_miners():
        """Get all miners with their data from database."""
        miners = get_all_miner_data()
        return {
            'count': len(miners),
            'miners': miners
        }
    
    
    @app.get("/stats", tags=["Statistics"])
    def get_stats():
        """Get overall statistics."""
        validator = get_validator()
        
        # Calculate stats
        total_score = sum(float(s) for s in validator.scores)
        active_miners = sum(1 for s in validator.scores if s > 0)
        volumes = getattr(validator, 'miner_volumes', {})
        total_volume = sum(volumes.values()) if volumes else 0
        
        return {
            'block': validator.block,
            'step': validator.step,
            'total_miners': validator.metagraph.n,
            'active_miners': active_miners,
            'total_score': total_score,
            'total_weighted_volume': total_volume,
            'miners_with_volume': len([v for v in volumes.values() if v > 0])
        }
    
    
    # ==================== WALLET MAPPING ENDPOINTS ====================
    
    @app.post("/api/wallet-mapping", tags=["Wallet Mapping"])
    def register_wallet_mapping(request: WalletMappingRequest):
        """
        Register a wallet mapping between a Bittensor coldkey and EVM address.
        
        The frontend UI calls this endpoint after the user signs a message
        with their coldkey to prove ownership. The server verifies the
        signature and stores the mapping.
        
        Request body:
        - type: "wallet_mapping"
        - data.coldkey: SS58 Bittensor coldkey address
        - data.evmAddress: EVM wallet address (0x...)
        - data.signature: Hex signature (128 chars, no 0x prefix)
        - data.message: Signed message with <Bytes>...</Bytes> wrapper
        - data.timestamp: Unix timestamp in milliseconds
        - data.verified: UI validation passed (server still verifies)
        """
        try:
            # SECURITY: Reject all requests if signature verification is unavailable
            if not SIGNATURE_VERIFICATION_AVAILABLE:
                bt.logging.error("Wallet mapping rejected: signature verification not available")
                raise HTTPException(
                    status_code=503,
                    detail="Signature verification unavailable. Install substrateinterface."
                )
            
            # Validate request type
            if request.type != "wallet_mapping":
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid request type: {request.type}"
                )
            
            data = request.data
            
            # Validate coldkey format (SS58, starts with 5, 47-48 chars)
            if not data.coldkey.startswith('5') or len(data.coldkey) < 47:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid coldkey format"
                )
            
            # Validate EVM address format (0x prefix, 42 chars)
            if not data.evmAddress.startswith('0x') or len(data.evmAddress) != 42:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid EVM address format"
                )
            
            # Validate signature format (128 hex chars, no 0x prefix)
            if len(data.signature) != 128:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid signature length: expected 128, got {len(data.signature)}"
                )
            
            # Validate message format (must have <Bytes>...</Bytes> wrapper)
            if not data.message.startswith('<Bytes>') or not data.message.endswith('</Bytes>'):
                raise HTTPException(
                    status_code=400,
                    detail="Message must be wrapped in <Bytes>...</Bytes>"
                )
            
            # Verify the signature (cryptographic verification)
            is_valid = _verify_coldkey_signature(
                coldkey=data.coldkey,
                message=data.message,
                signature=data.signature
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid signature"
                )
            
            # Save the wallet mapping
            success = save_wallet_mapping(
                coldkey=data.coldkey,
                evm_address=data.evmAddress,
                signature=data.signature,
                message=data.message,
                timestamp=data.timestamp
            )
            
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save wallet mapping"
                )
            
            bt.logging.info(
                f"Wallet mapping registered: {data.coldkey[:10]}... -> {data.evmAddress[:10]}..."
            )
            
            return {"success": True}
            
        except HTTPException:
            raise
        except Exception as e:
            bt.logging.error(f"Error processing wallet mapping: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal error: {str(e)}"
            )
    
    
    @app.get("/api/wallet-mapping/{coldkey}", tags=["Wallet Mapping"])
    def get_wallet_mapping_for_coldkey(coldkey: str):
        """Get the wallet mapping for a specific coldkey."""
        mapping = get_wallet_mapping(coldkey)
        
        if not mapping:
            raise HTTPException(
                status_code=404,
                detail=f"No wallet mapping found for coldkey: {coldkey[:10]}..."
            )
        
        return mapping
    
    
    @app.get("/api/wallet-mappings", tags=["Wallet Mapping"])
    def list_wallet_mappings():
        """Get all registered wallet mappings."""
        mappings = get_all_wallet_mappings()
        return {
            'count': len(mappings),
            'mappings': mappings
        }


def start_api_server(
    validator, 
    host: str = None, 
    port: int = None
) -> Optional[threading.Thread]:
    """
    Start the API server in a background thread.
    
    Args:
        validator: The validator instance
        host: Host to bind to (default from const.py)
        port: Port to bind to (default from const.py)
        
    Returns:
        The thread running the server, or None if FastAPI not available
    """
    if not FASTAPI_AVAILABLE:
        bt.logging.warning("FastAPI not available, API server not started")
        return None
    
    host = host or API_HOST
    port = port or API_PORT
    
    set_validator(validator)
    
    def _run_server():
        uvicorn.run(
            app, 
            host=host, 
            port=port, 
            log_level="warning",
            access_log=False
        )
    
    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
    
    bt.logging.info(f"API server started at http://{host}:{port}")
    bt.logging.info(f"API docs available at http://{host}:{port}/docs")
    
    return thread
