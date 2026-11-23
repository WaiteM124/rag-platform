locals {
  bedrock_region = var.aws_region
  account_id     = data.aws_caller_identity.current.account_id

  bedrock_answer_model_id    = var.bedrock_answer_model_id
  bedrock_eval_judge_model   = var.bedrock_eval_judge_model_id
  bedrock_embedding_model_id = var.bedrock_embedding_model_id

  bedrock_anthropic_inference_profile_ids = [
    "eu.anthropic.claude-haiku-5-5",
    "eu.anthropic.claude-sonnet-5",
  ]

  bedrock_inference_profile_ids = distinct(concat(
    [local.bedrock_answer_model_id, local.bedrock_eval_judge_model],
    local.bedrock_anthropic_inference_profile_ids,
  ))

  bedrock_answer_foundation_model_id = trimprefix(local.bedrock_answer_model_id, "eu.")
  bedrock_judge_foundation_model_id  = trimprefix(local.bedrock_eval_judge_model, "eu.")

  bedrock_retained_anthropic_foundation_ids = [
    "anthropic.claude-haiku-5-5",
    "anthropic.claude-sonnet-5",
  ]

  bedrock_in_region_foundation_ids = distinct(concat(
    [
      local.bedrock_answer_foundation_model_id,
      local.bedrock_judge_foundation_model_id,
      local.bedrock_embedding_model_id,
    ],
    local.bedrock_retained_anthropic_foundation_ids,
  ))

  bedrock_inference_profile_arns = [
    for id in local.bedrock_inference_profile_ids :
    "arn:aws:bedrock:${local.bedrock_region}:${local.account_id}:inference-profile/${id}"
    if startswith(id, "eu.")
  ]

  bedrock_in_region_foundation_arns = [
    for id in local.bedrock_in_region_foundation_ids :
    "arn:aws:bedrock:${local.bedrock_region}::foundation-model/${id}"
  ]

  bedrock_eu_foundation_arns = [
    for id in distinct(concat(
      [local.bedrock_answer_foundation_model_id, local.bedrock_judge_foundation_model_id],
      local.bedrock_retained_anthropic_foundation_ids,
    )) :
    "arn:aws:bedrock:eu-*::foundation-model/${id}"
  ]

  bedrock_invoke_arns = distinct(concat(
    local.bedrock_inference_profile_arns,
    local.bedrock_in_region_foundation_arns,
    local.bedrock_eu_foundation_arns,
  ))
}