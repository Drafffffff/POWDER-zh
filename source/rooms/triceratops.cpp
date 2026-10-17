// Auto-generated .map file
// DO NOT HAND EDIT
// Generated from triceratops.map

#include "../map.h"
#include "../glbdef.h"

const SQUARE_NAMES glb_triceratops_squarelist[] =
{
SQUARE_WALL,	SQUARE_WALL,	SQUARE_WALL,	SQUARE_EMPTY,	
SQUARE_EMPTY,	SQUARE_EMPTY,	SQUARE_EMPTY,	SQUARE_DOOR,	
SQUARE_FLOOR,	SQUARE_WALL,	SQUARE_CORRIDOR,	SQUARE_CORRIDOR,	
SQUARE_CORRIDOR,	SQUARE_EMPTY,	SQUARE_WALL,	SQUARE_FLOOR,	
SQUARE_SECRETDOOR,	SQUARE_CORRIDOR,	SQUARE_CORRIDOR,	SQUARE_CORRIDOR,	
SQUARE_EMPTY,	SQUARE_WALL,	SQUARE_FLOOR,	SQUARE_WALL,	
SQUARE_CORRIDOR,	SQUARE_CORRIDOR,	SQUARE_CORRIDOR,	SQUARE_EMPTY,	
SQUARE_WALL,	SQUARE_DOOR,	SQUARE_WALL,	SQUARE_EMPTY,	
SQUARE_EMPTY,	SQUARE_EMPTY,	SQUARE_EMPTY
};

const PT2 glb_triceratops_moblist[] =
{
	{ 5, 3, MOB_TRICERATOP },
	{ 5, 1, MOB_TRICERATOP },
	{ -1, -1, MOB_NONE }
};

const PT2 glb_triceratops_itemlist[] =
{
	{ -1, -1, ITEM_NONE }
};

const PT2 glb_triceratops_itemtypelist[] =
{
	{ 4, 3, ITEMTYPE_ANY },
	{ 5, 2, ITEMTYPE_ARTIFACT },
	{ 4, 1, ITEMTYPE_ANY },
	{ -1, -1, ITEMTYPE_NONE }
};

const PT2 glb_triceratops_moblevellist[] =
{
	{ -1, -1, MOBLEVEL_NONE }
};

const PT2 glb_triceratops_intrinsiclist[] =
{
	{ -1, -1, INTRINSIC_NONE }
};

const PT2 glb_triceratops_squareflaglist[] =
{
	{ 2, 4, SQUAREFLAG_LIT },
	{ 1, 4, SQUAREFLAG_LIT },
	{ 0, 4, SQUAREFLAG_LIT },
	{ 2, 3, SQUAREFLAG_LIT },
	{ 1, 3, SQUAREFLAG_LIT },
	{ 0, 3, SQUAREFLAG_LIT },
	{ 2, 2, SQUAREFLAG_LIT },
	{ 1, 2, SQUAREFLAG_LIT },
	{ 0, 2, SQUAREFLAG_LIT },
	{ 2, 1, SQUAREFLAG_LIT },
	{ 1, 1, SQUAREFLAG_LIT },
	{ 0, 1, SQUAREFLAG_LIT },
	{ 2, 0, SQUAREFLAG_LIT },
	{ 1, 0, SQUAREFLAG_LIT },
	{ 0, 0, SQUAREFLAG_LIT },
	{ -1, -1, SQUAREFLAG_NONE }
};

const PT2 glb_triceratops_signpostlist[] =
{
	{ -1, -1, SIGNPOST_NONE }
};

const ROOM_DEF glb_triceratops_roomdef =
{
	{ 7, 5, 0 },
	glb_triceratops_squarelist,
	glb_triceratops_squareflaglist,
	glb_triceratops_itemlist,
	glb_triceratops_moblist,
	glb_triceratops_itemtypelist,
	glb_triceratops_moblevellist,
	glb_triceratops_intrinsiclist,
	glb_triceratops_signpostlist,
	9, -1,
	100,
	0, 0,
	0,
	1,
	1,
	1,
	1,
	-1, -1, 
	-1, 
	"triceratops"
};
