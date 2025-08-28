from typing import List
from fastapi import APIRouter, HTTPException, Depends, Request

from app.api.schemas import CreateSimRequest

router = APIRouter(prefix="/simulations", tags=["simulations"])

def get_service(request: Request):
    svc = getattr(request.app.state, "sim_service", None)
    if svc is None:
        raise HTTPException(500, "Simulation service not initialized")
    return svc

@router.post("")
def create_sim(req: CreateSimRequest, svc = Depends(get_service)):
    if len(req.profiles) != len(req.agent_names):
        raise HTTPException(400, "profiles and agent_names must have same length")
    sim_id = svc.create_sim(
        topic=req.topic,
        profiles=req.profiles,
        agent_names=req.agent_names,
        max_iters=req.max_iters,
        bias=req.bias,
        stance=req.stance,
        embedding_model=req.embedding_model,
        embedding_config=req.embedding_config or {},
    )
    return {"id": sim_id, "snapshot": svc.snapshot(sim_id)}

@router.post("/{sim_id}/start")
def start_sim(sim_id: str, svc = Depends(get_service)):
    svc.start(sim_id)
    return {"id": sim_id, "snapshot": svc.snapshot(sim_id)}

@router.post("/{sim_id}/step")
def step(sim_id: str, svc = Depends(get_service)):
    event = svc.step(sim_id)
    return {"id": sim_id, "event": event, "snapshot": svc.snapshot(sim_id)}

@router.post("/{sim_id}/run")
def run(sim_id: str, svc = Depends(get_service)):
    svc.run(sim_id)
    return {"id": sim_id, "snapshot": svc.snapshot(sim_id)}

@router.post("/{sim_id}/vote")
def vote(sim_id: str, svc = Depends(get_service)):
    yea, nay, reasons = svc.vote(sim_id)
    return {"id": sim_id, "yea": yea, "nay": nay, "reasons": reasons}

@router.post("/{sim_id}/stop")
def stop(sim_id: str, svc = Depends(get_service)):
    svc.stop(sim_id)
    return {"id": sim_id, "snapshot": svc.snapshot(sim_id)}

@router.get("/{sim_id}")
def snapshot(sim_id: str, svc = Depends(get_service)):
    return svc.snapshot(sim_id)
