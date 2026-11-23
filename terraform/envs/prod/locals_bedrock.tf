locals {
  bedrock_region = var.aws_region
  account_id     = data.aws_caller_identity.current.account_id

  bedrock_answer_model_id    = var.bedrock_answer_model_id
  bedrock_eval_judge_model   = var.bedrock_eval_judge_model_id
  bedrock_embedding_model_id = var.bedrock_embedding_model_id

  bedrock_answer_foundation_model_id = trimprefix(local.bedrock_answer_model_id, "eu.")
  bedrock_judge_foundation_model_id  = trimprefix(local.bedrock_eval_judge_model, "eu.")

  bedrock_inference_profile_arns = [
    "arn:aws:bedrock:${local.bedrock_region}:${local.account_id}:inference-profile/${local.bedrock_answer_model_id}",
    "arn:aws:bedrock:${local.bedrock_region}:${local.account_id}:inference-profile/${local.bedrock_eval_judge_model}",
  ]

  bedrock_invoke_arns = concat(
    local.bedrock_inference_profile_arns,
    [
      "arn:aws:bedrock:eu-*::foundation-model/${local.bedrock_answer_foundation_model_id}",
      "arn:aws:bedrock:eu-*::foundation-model/${local.bedrock_judge_foundation_model_id}",
      "arn:aws:bedrock:${local.bedrock_region}::foundation-model/${local.bedrock_embedding_model_id}",
    ],
  )
}