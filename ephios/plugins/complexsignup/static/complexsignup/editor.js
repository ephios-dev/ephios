const {createApp, ref, onUpdated, computed, watch, nextTick} = Vue

document.addEventListener('DOMContentLoaded', (event) => {
    const blocksInput = document.getElementById("id_blocks");
    const blocksInputValue = blocksInput.value;
    blocksInput.value = "";
    const qualifications = JSON.parse(document.getElementById("qualifications_json").value);

    createApp({
        setup() {
            const blockNameInput = ref(null);
            const currentBlock = ref(null);
            const blocks = ref(blocksInputValue ? JSON.parse(blocksInputValue) : []);
            blocks.value.forEach(block => {
                block.deleted = false;
                block.created = false;
                block.positions.forEach(position => {
                    position.clientId = `${position.id}`;
                });
                block.qualification_requirements.forEach(requirement => {
                    requirement.clientId = `${requirement.id}`;
                });
                block.sub_compositions.forEach(sub_composition => {
                    sub_composition.clientId = `${sub_composition.id}`;
                });
            });

            async function addBlock(block_type) {
                const newBlock = {
                    block_type: block_type,
                    name: "",
                    allowMore: false,
                    positions: [],
                    qualification_requirements: [],
                    sub_compositions: [],
                    id: self.crypto.randomUUID(),
                    created: true,
                }
                blocks.value.push(newBlock);
                currentBlock.value = newBlock;
                await nextTick()
                blockNameInput.value.focus();
            }

            function selectBlock(block) {
                currentBlock.value = block;
            }

            function removeBlock(block) {
                block.deleted = true;
                if (block.created) {
                    // remove block from list if it was not saved yet
                    blocks.value = blocks.value.filter(b => b.id !== block.id);
                }
                if (currentBlock.value === block) {
                    currentBlock.value = null;
                }
                // remove this block from all sub_compositions
                blocks.value.forEach(b => {
                    b.sub_compositions = b.sub_compositions.filter(sc => sc.sub_block !== block.id);
                });
            }

            function addPosition(e) {
                currentBlock.value.positions.push({
                        optional: false,
                        label: "",
                        qualifications: [],
                        id: null,
                        clientId: `new-${Math.random().toString(36).substring(7)}`,
                    }
                );
            }

            function removePosition(position) {
                currentBlock.value.positions = currentBlock.value.positions.filter(p => p.clientId !== position.clientId);
            }

            function addQualificationRequirement(e) {
                currentBlock.value.qualification_requirements.push({
                        id: null,
                        clientId: `new-${Math.random().toString(36).substring(7)}`,
                        qualifications: [],
                        at_least: 1,
                        everyone: false,
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

            function getBlockById(id) {
                return blocks.value.find(b => b.id === id);
            }

            function getSubBlocks(block) {
                const subBlocks = [];
                block.sub_compositions.forEach(composition => {
                    const sub_block = getBlockById(composition.sub_block);
                    if (!sub_block) {
                        return;
                    }
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

            function canAddSubBlock(block, sub_block) {
                if (!block || block.block_type !== 'composite' || !sub_block || block.id === sub_block.id) {
                    return false;
                }
                // check if block is a descendant of sub_block
                return !getDescendants(sub_block).some(descendant => descendant.id === block.id);
            }

            function addSubComposition(block, sub_block) {
                block.sub_compositions.push({
                    sub_block: sub_block.id,
                    optional: false,
                    id: null,
                    clientId: `new-${Math.random().toString(36).substring(7)}`,
                });
            }

            function removeSubComposition(block, composition) {
                block.sub_compositions = block.sub_compositions.filter(c => c !== composition);
            }

            function getParticipantCount(block) {
                let min = 0;
                let max = 0;
                let allowMore = false;


                block.sub_compositions.forEach(composition => {
                    const sub_block = getBlockById(composition.sub_block);
                    const {min: sub_min, max: sub_max, allowMore: sub_allowMore} = getParticipantCount(sub_block);
                    if(!composition.optional) {
                        min += sub_min;
                    }
                    max += sub_max;
                    allowMore = allowMore || sub_allowMore;
                });

                block.positions.forEach(position => {
                    if (!position.optional) {
                        min += 1;
                    }
                    max += 1;
                });
                allowMore = allowMore || block.allowMore;
                return {min, max, allowMore};
            }

            function participantCountInfo(block) {
                const {min, max, allowMore} = getParticipantCount(block);
                if (allowMore) {
                    return gettext("{min}+").replace("{min}", min);
                }
                if (min === max) {
                    return min;
                }
                return gettext("{min} to {max}").replace("{min}", min).replace("{max}", max);
            }

            const undeletedBlocks = computed(() => blocks.value.filter(b => !b.deleted));


            return {
                blocks,
                qualifications,
                currentBlock,
                undeletedBlocks,

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
            }
        },
        delimiters: ['[[', ']]']
    }).mount('#editor');
});