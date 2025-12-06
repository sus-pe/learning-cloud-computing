from typing import TYPE_CHECKING

from petstore_catalog import CreateNewPetRequest, PetEntity, PetTypeEntity

if TYPE_CHECKING:
    from petstore_catalog import PetStoreTester

GOLDY = PetEntity(name="goldy", birthdate="21-01-1984", picture="1.goldy.png")
GOLDY_REQUEST = CreateNewPetRequest.model_validate(
    {
        "name": GOLDY.name,
        "picture-url": "https://api-ninjas-data.s3.us-west-2.amazonaws.com/logos/lcc34f378eca756ae8657271b3da2605a848e1c82.png",
        "birthdate": GOLDY.birthdate,
    }
)
ROLDY = PetEntity(name="roldy", birthdate="21-01-1884", picture="1.roldy.png")
ROLDY_REQUEST = CreateNewPetRequest.model_validate(
    {
        "name": ROLDY.name,
        "picture-url": "https://api-ninjas-data.s3.us-west-2.amazonaws.com/logos/lb655fc3f19ed51e14db3ac88f6573a42231f7390.png",
        "birthdate": ROLDY.birthdate,
    }
)
GOLDEN_RETRIEVER = PetTypeEntity(
    id="1",
    type="English Cream Golden Retriever",
    family="Canidae",
    genus="Canis",
    attributes=["Intelligent", "and", "obedient"],
    lifespan=10,
    pets=[],
)

CHEETI = PetEntity(name="cheeti", birthdate="21-11-1384", picture="2.cheeti.png")
CHEETI_REQUEST = CreateNewPetRequest.model_validate(
    {
        "name": CHEETI.name,
        "picture-url": "https://api-ninjas-data.s3.us-west-2.amazonaws.com/logos/ledcd8710831cb501175dbcc70012726569200bf8.png",
        "birthdate": CHEETI.birthdate,
    }
)
KHEETI = PetEntity(name="kheeti", birthdate="11-12-1784", picture="2.kheeti.png")
KHEETI_REQUEST = CreateNewPetRequest.model_validate(
    {
        "name": KHEETI.name,
        "picture-url": "https://api-ninjas-data.s3.us-west-2.amazonaws.com/logos/lb526ce21f0c38c500cf190d853bde92cfa080e4e.png",
        "birthdate": KHEETI.birthdate,
    }
)


CHEETAH = PetTypeEntity(
    id="2",
    type="Cheetah",
    family="Felidae",
    genus="Acinonyx",
    attributes=["Solitary", "Pairs"],
    lifespan=10,
    pets=[],
)


async def test_e2e(tester: PetStoreTester) -> None:
    created_golden_retriever = await tester.post_new_pet_type(
        type_name=GOLDEN_RETRIEVER.type
    )
    assert created_golden_retriever == GOLDEN_RETRIEVER.model_copy(update={"pets": []})

    created_cheetah = await tester.post_new_pet_type(type_name=CHEETAH.type)
    assert created_cheetah == CHEETAH.model_copy(update={"pets": []})

    created_goldy = await tester.post_new_pet_request(
        GOLDEN_RETRIEVER.id, GOLDY_REQUEST
    )
    assert created_goldy == GOLDY
    created_roldy = await tester.post_new_pet_request(
        GOLDEN_RETRIEVER.id, ROLDY_REQUEST
    )
    assert created_roldy == ROLDY

    created_cheeti = await tester.post_new_pet_request(CHEETAH.id, CHEETI_REQUEST)
    assert created_cheeti == CHEETI
    created_kheeti = await tester.post_new_pet_request(CHEETAH.id, KHEETI_REQUEST)
    assert created_kheeti == KHEETI
