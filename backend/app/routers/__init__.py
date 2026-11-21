"""One router per resource. Each function is one endpoint; its signature (path,
body model, return type) is the contract. Bodies are stubs until the slice that
implements them (HANDOFF §11)."""
