from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import crud
from app.db.models import LoadBalancerHost as LoadBalancerHostDbModel
from app.db.models import Node as NodeDbModel  # Assuming Node model might be needed
from app.db import get_db
from app.models.admin import Admin
from app.models.load_balancer import (
    LoadBalancerHostCreate,
    LoadBalancerHostResponse,
    LoadBalancerHostUpdate,
)
from app.utils import responses

router = APIRouter(
    prefix="/api/load-balancer-hosts",
    tags=["Load Balancer Hosts"],
    responses={401: responses._401, 403: responses._403}
)

@router.post("/", response_model=LoadBalancerHostResponse, status_code=201)
def create_load_balancer_host(
    lb_host_create: LoadBalancerHostCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Create a new Load Balancer Host."""
    # Check if inbound tag exists
    inbound = crud.get_or_create_inbound(db, lb_host_create.inbound_tag)
    if not inbound:
        # This case should ideally not be hit if get_or_create_inbound works as expected
        raise HTTPException(status_code=404, detail=f"Inbound tag '{lb_host_create.inbound_tag}' not found and could not be created.")

    # Check if all node_ids exist
    if lb_host_create.node_ids:
        found_nodes = db.query(crud.Node).filter(crud.Node.id.in_(lb_host_create.node_ids)).all()
        if len(found_nodes) != len(set(lb_host_create.node_ids)):
            raise HTTPException(status_code=404, detail="One or more Node IDs not found.")
    try:
        db_lb_host = crud.create_load_balancer_host(db=db, lb_host_create=lb_host_create)
    except IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: load_balancer_hosts.name" in str(e.orig):
            raise HTTPException(status_code=409, detail=f"Load Balancer Host with name '{lb_host_create.name}' already exists.")
        elif "UNIQUE constraint failed: _lb_host_uc" in str(e.orig) or "load_balancer_hosts.address, load_balancer_hosts.port, load_balancer_hosts.inbound_tag, load_balancer_hosts.sni" in str(e.orig):
             raise HTTPException(status_code=409, detail="A Load Balancer Host with the same address, port, inbound_tag, and SNI already exists.")
        else:
            raise HTTPException(status_code=500, detail=f"Database integrity error: {e.orig}")

    return db_lb_host


@router.get("/", response_model=List[LoadBalancerHostResponse])
def get_all_load_balancer_hosts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.get_current_admin),
):
    """Retrieve all Load Balancer Hosts."""
    return crud.get_all_load_balancer_hosts(db=db, skip=skip, limit=limit)


@router.get("/{lb_host_id}", response_model=LoadBalancerHostResponse)
def get_load_balancer_host(
    lb_host_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.get_current_admin),
):
    """Retrieve a specific Load Balancer Host by ID."""
    db_lb_host = crud.get_load_balancer_host(db=db, lb_host_id=lb_host_id)
    if db_lb_host is None:
        raise HTTPException(status_code=404, detail="Load Balancer Host not found")
    return db_lb_host


@router.put("/{lb_host_id}", response_model=LoadBalancerHostResponse)
def update_load_balancer_host(
    lb_host_id: int,
    lb_host_update: LoadBalancerHostUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Update a Load Balancer Host."""
    db_lb_host = crud.get_load_balancer_host(db, lb_host_id=lb_host_id)
    if not db_lb_host:
        raise HTTPException(status_code=404, detail="Load Balancer Host not found")

    # Check if all node_ids exist if provided
    if lb_host_update.node_ids:
        found_nodes = db.query(crud.Node).filter(crud.Node.id.in_(lb_host_update.node_ids)).all()
        if len(found_nodes) != len(set(lb_host_update.node_ids)):
            raise HTTPException(status_code=404, detail="One or more Node IDs in the update list not found.")
    
    # If inbound_tag is being changed, verify the new one exists or can be created
    if lb_host_update.inbound_tag and lb_host_update.inbound_tag != db_lb_host.inbound_tag:
        inbound = crud.get_or_create_inbound(db, lb_host_update.inbound_tag)
        if not inbound:
             raise HTTPException(status_code=404, detail=f"New inbound tag '{lb_host_update.inbound_tag}' not found and could not be created.")

    try:
        updated_lb_host = crud.update_load_balancer_host(db=db, lb_host_id=lb_host_id, lb_host_update=lb_host_update)
    except IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: load_balancer_hosts.name" in str(e.orig):
            raise HTTPException(status_code=409, detail=f"Load Balancer Host with name '{lb_host_update.name}' already exists for another entry.")
        elif "UNIQUE constraint failed: _lb_host_uc" in str(e.orig) or "load_balancer_hosts.address, load_balancer_hosts.port, load_balancer_hosts.inbound_tag, load_balancer_hosts.sni" in str(e.orig):
             raise HTTPException(status_code=409, detail="Another Load Balancer Host with the same address, port, inbound_tag, and SNI already exists.")
        else:
            raise HTTPException(status_code=500, detail=f"Database integrity error during update: {e.orig}")
    return updated_lb_host


@router.delete("/{lb_host_id}", status_code=204)
def delete_load_balancer_host(
    lb_host_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Delete a Load Balancer Host."""
    db_lb_host = crud.delete_load_balancer_host(db=db, lb_host_id=lb_host_id)
    if db_lb_host is None:
        raise HTTPException(status_code=404, detail="Load Balancer Host not found")
    return None # Returns 204 No Content on success 