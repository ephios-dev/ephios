const {createApp, ref, onUpdated, computed, onMounted, nextTick} = Vue

function randomClientId() {
    return `${Math.random().toString(36).substring(7)}`;
}

document.addEventListener('DOMContentLoaded', (event) => {
    const blocksInput = document.getElementById("id_blocks");
    const blocksInputValue = blocksInput.value;
    blocksInput.value = "";
    const qualifications = JSON.parse(document.getElementById("qualifications_json").value);

    createApp({
        setup() {
            const currentBlock = ref(null);
            const searchQuery = ref("");
            const blocks = ref(blocksInputValue ? JSON.parse(blocksInputValue) : []);
            blocks.value.forEach(block => {
                block.deleted = false;
                block.created = !block.id;
                block.invalidFields = [];
                block.positions.forEach(position => {
                    position.clientId = `${position.id}`;
                });
                block.qualification_requirements.forEach(requirement => {
                    requirement.clientId = `${requirement.id}`;
                });
                block.sub_compositions.forEach(sub_composition => {
                    sub_composition.clientId = `${sub_composition.id}`;
                });
                validateBlock(block);
            })

            async function addBlock(block_type, copy_from) {
                const newBlock = {
                    uuid: self.crypto.randomUUID(),
                    created: true,
                    deleted: false,
                    invalidFields: [],
                    block_type: block_type,
                    name: "",
                    allow_more: false,
                    positions: [],
                    qualification_requirements: [],
                    sub_compositions: [],
                }
                if (copy_from) {
                    let i = 2;
                    while (blocks.value.some(b => b.name === `${copy_from.name} ${i}`)) {
                        i++;
                    }
                    newBlock.name = `${copy_from.name} ${i}`;
                    newBlock.allow_more = copy_from.allow_more;
                    newBlock.positions = copy_from.positions.map(p => ({
                        ...p,
                        id: null,
                        clientId: randomClientId()
                    }));
                    newBlock.qualification_requirements = copy_from.qualification_requirements.map(q => ({
                        ...q,
                        id: null,
                        clientId: randomClientId()
                    }));
                    newBlock.sub_compositions = copy_from.sub_compositions.map(sc => ({
                        ...sc,
                        id: null,
                        clientId: randomClientId()
                    }));
                }
                validateBlock(currentBlock.value);
                blocks.value.push(newBlock);
                currentBlock.value = newBlock;
                await nextTick()
                document.getElementById("blockNameInput").focus();
            }


            async function selectBlock(block) {
                if (currentBlock.value === block) {
                    return;
                }
                validateBlock(currentBlock.value);
                currentBlock.value = block;
                await nextTick();
                validateBlock(currentBlock.value);
            }

            function removeBlock(block) {
                block.deleted = true;
                if (block.created) {
                    // remove block from list if it was not saved yet
                    blocks.value = blocks.value.filter(b => b.uuid !== block.uuid);
                }
                if (currentBlock.value === block) {
                    currentBlock.value = null;
                }
                // remove this block from all sub_compositions
                blocks.value.forEach(b => {
                    b.sub_compositions = b.sub_compositions.filter(sc => sc.sub_block !== block.uuid);
                });
            }

            function addPosition(e) {
                currentBlock.value.positions.push({
                        optional: false,
                        label: "",
                        qualifications: [],
                        id: null,
                        clientId: randomClientId(),
                    }
                );
            }

            function removePosition(position) {
                currentBlock.value.positions = currentBlock.value.positions.filter(p => p.clientId !== position.clientId);
            }

            function addQualificationRequirement(e) {
                currentBlock.value.qualification_requirements.push({
                        id: null,
                        clientId: randomClientId(),
                        qualifications: [],
                        at_least: 1,
                        everyone: true,
                    }
                );
            }

            function removeQualificationRequirement(requirement) {
                currentBlock.value.qualification_requirements = currentBlock.value.qualification_requirements.filter(r => r.clientId !== requirement.clientId);
            }

            function addQualificationToObjectFromSelect(event, object) {
                if (!event.target.value) {
                    return;
                }
                const newQualification = parseInt(event.target.value);
                event.target.value = "";
                if (!object.qualifications.some(q => q === newQualification)) {
                    object.qualifications.push(newQualification);
                }
            }

            function removeQualificationFromObject(object, qualification_id) {
                object.qualifications = object.qualifications.filter(q => q !== qualification_id);
            }

            function addableQualifications(existing_ids) {
                return Object.values(qualifications).filter(q => !existing_ids.some(existing_id => qualifications[existing_id].included.includes(q.id)));
            }

            onUpdated(() => {
                handleForms($('#editor'));
            });

            onMounted(async () => {
                const firstInvalidBlock = blocks.value.find(block => !!block.invalidFields.length);
                if (firstInvalidBlock) {
                    await selectBlock(firstInvalidBlock);
                    await nextTick();
                    document.getElementById("blockNameInput").focus();
                }
            });

            function getBlockById(uuid) {
                return blocks.value.find(b => b.uuid === uuid);
            }

            function getSubBlocks(block) {
                const subBlocks = [];
                block.sub_compositions.forEach(composition => {
                    const sub_block = getBlockById(composition.sub_block);
                    if (!sub_block) {
                        return;
                    }
                    sub_block.sub_label = composition.label;  // provide the label as an additional attribute
                    subBlocks.push(sub_block);
                });
                return subBlocks;
            }

            function getDescendants(block) {
                const descendants = [];
                getSubBlocks(block).forEach(sub_block => {
                    descendants.push(sub_block);
                    descendants.push(...getDescendants(sub_block));
                });
                // remove duplicates
                return [...new Set(descendants)];
            }

            function canAddSubBlock(block, candidate) {
                if (!block || block.block_type !== 'composite' || !candidate || block.uuid === candidate.uuid) {
                    return false;
                }
                // check if block is a descendant of sub_block
                return !getDescendants(candidate).some(descendant => descendant.uuid === block.uuid);
            }

            function addSubComposition(block, sub_block) {
                block.sub_compositions.push({
                    sub_block: sub_block.uuid,
                    optional: false,
                    label: "",
                    id: null,
                    clientId: randomClientId(),
                });
            }

            function removeSubComposition(block, composition) {
                block.sub_compositions = block.sub_compositions.filter(c => c !== composition);
            }

            function getParticipantCount(block) {
                let min = 0;
                let max = 0;
                let allow_more = false;


                block.sub_compositions.forEach(composition => {
                    const sub_block = getBlockById(composition.sub_block);
                    const {min: sub_min, max: sub_max, allow_more: sub_allow_more} = getParticipantCount(sub_block);
                    if (!composition.optional) {
                        min += sub_min;
                    }
                    max += sub_max;
                    allow_more = allow_more || sub_allow_more;
                });

                block.positions.forEach(position => {
                    if (!position.optional) {
                        min += 1;
                    }
                    max += 1;
                });
                allow_more = allow_more || block.allow_more;
                return {min, max, allow_more};
            }

            function participantCountInfo(block) {
                const {min, max, allow_more} = getParticipantCount(block);
                if (allow_more) {
                    return gettext("{min}+").replace("{min}", min);
                }
                if (min === max) {
                    return min;
                }
                return gettext("{min} to {max}").replace("{min}", min).replace("{max}", max);
            }

            const blocksSearched = computed(() => {
                let ret = blocks.value.filter(b => !b.deleted)
                if (searchQuery.value) {
                    ret = ret.filter(b => b.name.toLowerCase().includes(searchQuery.value.toLowerCase()));
                }
                return ret;
            });

            function submitForm(event) {
                event.target.submit();
            }

            function validateBlock(block) {
                /*
                * Validate a block: return true if block is valid, also save invalid
                * fields as attribute.
                * Is called on selecting a block on the old and new block.
                 */
                if (!block) {
                    return false;
                }
                let invalidFields = [];
                if (!block.name) {
                    invalidFields.push("name");
                }
                block.invalidFields = invalidFields;
                return !invalidFields.length;
            }

            return {
                blocks,
                qualifications,
                currentBlock,
                searchQuery,
                blocksSearched,

                addBlock,
                selectBlock,
                removeBlock,

                canAddSubBlock,
                addSubComposition,
                removeSubComposition,

                addPosition,
                removePosition,
                addQualificationToObjectFromSelect,
                removeQualificationFromObject,
                addQualificationRequirement,
                removeQualificationRequirement,

                participantCountInfo,
                getSubBlocks,
                getBlockById,
                addableQualifications,

                validateBlock,
                submitForm,
            }
        },
        delimiters: ['[[', ']]']
    }).mount('#editor');
});